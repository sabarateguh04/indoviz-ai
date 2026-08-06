"""1 worker per RTSP stream: decode + infer + track + jalankan semua modul
di `analytics/` + broadcast hasil via websocket + simpan histori ke DB.

Worker jalan di thread terpisah (bukan async) karena `cv2.VideoCapture.read()`
blocking. Broadcast ke websocket (yang hidup di event loop asyncio utama
FastAPI/Uvicorn) dikirim lewat `asyncio.run_coroutine_threadsafe`.

Daftar kamera aktif & poligon zona dibaca dari database (bukan hardcode di
.env) — `StreamWorkerManager` bisa start/stop worker per kamera secara
dinamis saat kamera ditambah/diedit/dihapus dari UI, tanpa restart backend.
"""
import asyncio
import base64
import logging
import threading
import time
from collections import deque

import cv2

from app.analytics import congestion, counting, illegal_parking, lane_violation, wrong_way
from app.analytics import speed as speed_analytics
from app.api.routes_ws import ws_manager
from app.config import settings
from app.core.detector import VehicleDetector
from app.core.state import CameraState
from app.core.tracker import extract_detections
from app.core.zones import RuntimeZone
from app.db import store

logger = logging.getLogger(__name__)

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


def _broadcast(payload: dict):
    if _main_loop is None:
        return
    asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), _main_loop)


ZONE_REFRESH_INTERVAL = 5.0  # detik — supaya perubahan zona dari UI kepakai tanpa restart
RECONNECT_DELAY = 3.0
FRAME_JPEG_MAX_WIDTH = 960
FRAME_JPEG_QUALITY = 70


def _encode_frame_b64(frame) -> str | None:
    """Encode frame jadi JPEG base64 utk dikirim ke frontend sebagai video
    (tahap awal, sebelum ada pipeline HLS/WebRTC terpisah). Di-resize dulu
    supaya payload websocket tidak terlalu besar untuk banyak stream
    sekaligus."""
    h, w = frame.shape[:2]
    if w > FRAME_JPEG_MAX_WIDTH:
        scale = FRAME_JPEG_MAX_WIDTH / w
        frame = cv2.resize(frame, (FRAME_JPEG_MAX_WIDTH, int(h * scale)))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, FRAME_JPEG_QUALITY])
    if not ok:
        return None
    return base64.b64encode(buf).decode("ascii")


class StreamWorker(threading.Thread):
    def __init__(self, camera_id: int):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self._stop_event = threading.Event()
        self.state = CameraState()
        self.zones: list[RuntimeZone] = []
        self._last_zone_refresh = 0.0
        self._last_cleanup = 0.0
        self._frame_times: deque = deque(maxlen=30)

    def stop(self):
        self._stop_event.set()

    def _load_zones(self):
        rows = store.list_zones(self.camera_id)
        self.zones = [
            RuntimeZone(
                id=z.id,
                camera_id=z.camera_id,
                nama=z.nama or "",
                tipe_zona=z.tipe_zona,
                koordinat=[tuple(p) for p in z.koordinat],
                arah_normal_deg=z.arah_normal_deg,
            )
            for z in rows
        ]
        self._last_zone_refresh = time.time()

    def _set_status(self, status: str):
        store.set_camera_status(self.camera_id, status)

    def run(self):
        camera = store.get_camera(self.camera_id)
        if camera is None:
            return
        rtsp_url = camera.rtsp_url
        imgsz = camera.imgsz or settings.IMGSZ_DEFAULT
        self._load_zones()

        detector = VehicleDetector.get_shared()
        cap = cv2.VideoCapture(rtsp_url)
        consecutive_failures = 0
        last_broadcast = 0.0

        self._set_status("online" if cap.isOpened() else "offline")

        try:
            while not self._stop_event.is_set():
                if not cap.isOpened():
                    self._set_status("offline")
                    time.sleep(RECONNECT_DELAY)
                    cap.release()
                    cap = cv2.VideoCapture(rtsp_url)
                    continue

                ok, frame = cap.read()
                if not ok or frame is None:
                    consecutive_failures += 1
                    self._set_status("warning" if consecutive_failures < 10 else "offline")
                    time.sleep(0.5)
                    if consecutive_failures >= 10:
                        cap.release()
                        cap = cv2.VideoCapture(rtsp_url)
                        consecutive_failures = 0
                    continue

                consecutive_failures = 0
                self._set_status("online")
                now = time.time()
                self._frame_times.append(now)

                if now - self._last_zone_refresh > ZONE_REFRESH_INTERVAL:
                    self._load_zones()
                    camera = store.get_camera(self.camera_id)
                    if camera is None:
                        break  # kamera sudah dihapus dari UI
                    if not camera.active:
                        break  # kamera dinonaktifkan dari UI

                result = detector.track(frame, imgsz=imgsz)
                detections = extract_detections(result)

                for det in detections:
                    self.state.update_track_position(det.track_id, det.class_name, det.centroid, now)

                if now - self._last_cleanup > 10:
                    self.state.cleanup_stale(now)
                    self._last_cleanup = now

                count_events = counting.process(detections, self.zones, self.state)
                speeds = speed_analytics.process(detections, self.state, camera.speed_calibration)
                wrong_way_events = wrong_way.process(detections, self.zones, self.state)
                parking_events = illegal_parking.process(detections, self.zones, self.state, frame.shape)
                congestion_status = congestion.process(detections, self.zones, self.state)
                lane_events = lane_violation.process(detections, self.zones, self.state)

                if count_events or wrong_way_events or parking_events or lane_events:
                    self._persist_events(count_events, wrong_way_events, parking_events, lane_events)

                if now - last_broadcast >= settings.WS_BROADCAST_INTERVAL:
                    last_broadcast = now
                    fps = 0.0
                    if len(self._frame_times) > 1:
                        span = self._frame_times[-1] - self._frame_times[0]
                        fps = round((len(self._frame_times) - 1) / span, 1) if span > 0 else 0.0
                    # Dicek fresh tiap tick (bukan cuma tiap ZONE_REFRESH_INTERVAL)
                    # supaya tombol play/pause di UI terasa responsif.
                    fresh_camera = store.get_camera(self.camera_id)
                    view_enabled = fresh_camera.view_enabled if fresh_camera else True
                    self._broadcast_frame_data(
                        frame, fps, view_enabled, detections, speeds, congestion_status, count_events,
                        wrong_way_events, parking_events, lane_events,
                    )
        finally:
            cap.release()
            self._set_status("offline")

    def _persist_events(self, count_events, wrong_way_events, parking_events, lane_events):
        if count_events:
            store.append_count_events(self.camera_id, count_events)

        alerts = []
        for ev in wrong_way_events:
            alerts.append({"zone_id": ev.zone_id, "tipe": "wrong_way", "track_id": ev.track_id,
                            "pesan": f"Kendaraan {ev.kelas} melawan arah"})
        for ev in parking_events:
            alerts.append({"zone_id": ev.zone_id, "tipe": "illegal_parking", "track_id": ev.track_id,
                            "pesan": f"Kendaraan {ev.kelas} berhenti {ev.durasi_detik:.0f}s di zona larangan parkir"})
        for ev in lane_events:
            alerts.append({"zone_id": ev.zone_id, "tipe": "lane_violation", "track_id": ev.track_id,
                            "pesan": f"Kendaraan {ev.kelas} keluar dari jalur"})
        if alerts:
            store.append_alerts(self.camera_id, alerts)

    def _broadcast_frame_data(self, frame, fps, view_enabled, detections, speeds, congestion_status, count_events,
                               wrong_way_events, parking_events, lane_events):
        height, width = frame.shape[:2]
        payload = {
            "type": "frame_update",
            "camera_id": self.camera_id,
            "timestamp": time.time(),
            "fps": fps,
            "frame_width": width,
            "frame_height": height,
            # Kalau view_enabled false, JPEG tidak di-encode sama sekali
            # (hemat CPU + bandwidth) — tapi deteksi/counting/alert di bawah
            # ini tetap dikirim penuh, jadi counting & alert tetap real-time
            # walau live view dimatikan.
            "view_enabled": view_enabled,
            "frame_jpeg_b64": _encode_frame_b64(frame) if view_enabled else None,
            "detections": [
                {
                    "track_id": d.track_id,
                    "kelas": d.class_name,
                    "conf": round(d.conf, 2),
                    "bbox": d.bbox,
                    "kecepatan_kmh": speeds.get(d.track_id),
                }
                for d in detections
            ],
            "congestion": [
                {"zone_id": c.zone_id, "jumlah": c.jumlah_saat_ini, "rata_rata": c.rata_rata, "level": c.level}
                for c in congestion_status
            ],
            "counts": [{"zone_id": e.zone_id, "track_id": e.track_id, "kelas": e.kelas} for e in count_events],
            "alerts": (
                [{"tipe": "wrong_way", "zone_id": e.zone_id, "track_id": e.track_id, "kelas": e.kelas}
                 for e in wrong_way_events]
                + [{"tipe": "illegal_parking", "zone_id": e.zone_id, "track_id": e.track_id, "kelas": e.kelas,
                    "durasi_detik": e.durasi_detik} for e in parking_events]
                + [{"tipe": "lane_violation", "zone_id": e.zone_id, "track_id": e.track_id, "kelas": e.kelas}
                   for e in lane_events]
            ),
        }
        _broadcast(payload)


class StreamWorkerManager:
    """Start/stop worker per kamera secara dinamis — dipanggil saat startup
    (sinkron dengan kamera aktif di DB) dan dari routes_cameras setiap ada
    tambah/edit/hapus/nonaktifkan kamera, tanpa restart backend."""

    def __init__(self):
        self.workers: dict[int, StreamWorker] = {}
        self._lock = threading.Lock()

    def start_camera(self, camera_id: int):
        with self._lock:
            existing = self.workers.get(camera_id)
            if existing and existing.is_alive():
                return
            worker = StreamWorker(camera_id)
            self.workers[camera_id] = worker
            worker.start()
            logger.info("Worker started for camera_id=%s", camera_id)

    def stop_camera(self, camera_id: int):
        with self._lock:
            worker = self.workers.pop(camera_id, None)
        if worker:
            worker.stop()
            logger.info("Worker stop requested for camera_id=%s", camera_id)

    def restart_camera(self, camera_id: int):
        self.stop_camera(camera_id)
        self.start_camera(camera_id)

    def refresh_from_db(self):
        """Sinkronkan worker yang berjalan dengan daftar kamera aktif di
        penyimpanan JSON. Dipanggil saat startup aplikasi."""
        active_cameras = store.list_active_cameras()
        active_ids = {c.id for c in active_cameras}
        with self._lock:
            running_ids = set(self.workers.keys())

        for cam_id in active_ids - running_ids:
            self.start_camera(cam_id)
        for cam_id in running_ids - active_ids:
            self.stop_camera(cam_id)

    def shutdown_all(self):
        with self._lock:
            workers = list(self.workers.values())
            self.workers.clear()
        for w in workers:
            w.stop()


worker_manager = StreamWorkerManager()
