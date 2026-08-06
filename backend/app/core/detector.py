"""Wrapper YOLO (ultralytics) untuk deteksi kendaraan.

Model nano (YOLOv8n / YOLO11n) dipakai supaya bisa jalan multi-stream di
satu GPU. Confidence threshold dipisah per kelas karena motor (objek kecil)
butuh threshold lebih rendah dibanding mobil/bus/truk supaya tidak banyak
miss detection.
"""
import logging
import threading

import cv2
import torch
from ultralytics import YOLO

from app.config import settings

logger = logging.getLogger(__name__)


def _pick_device() -> str:
    """`YOLO_DEVICE=auto` (default) -> pakai GPU kalau CUDA kedetect oleh
    torch, fallback CPU kalau tidak. Kalau GPU ada tapi tidak kepakai
    (mis. torch ke-install versi CPU-only), inferensi tetap jalan di CPU
    -- lebih lambat & attention/akurasi model besar jadi tidak feasible
    real-time, tapi tidak bikin deteksi gagal total."""
    forced = (settings.YOLO_DEVICE or "auto").strip().lower()
    if forced not in ("", "auto"):
        return settings.YOLO_DEVICE
    if torch.cuda.is_available():
        return "cuda:0"
    logger.warning(
        "CUDA tidak terdeteksi oleh torch (torch=%s) — inferensi YOLO jalan di CPU. "
        "Kalau ada GPU NVIDIA terpasang, kemungkinan torch yang ke-install adalah "
        "build CPU-only; install ulang torch dengan build CUDA yang sesuai "
        "(lihat https://pytorch.org/get-started/locally/) supaya GPU kepakai.",
        torch.__version__,
    )
    return "cpu"


def _enhance_low_light(frame):
    """CLAHE (contrast-limited adaptive histogram equalization) pada channel
    luminance -- dipanggil hanya kalau kecerahan rata-rata frame di bawah
    `LOW_LIGHT_BRIGHTNESS_THRESHOLD`. Model YOLO (dilatih di COCO, mayoritas
    foto siang/warna) cenderung kurang percaya diri di footage CCTV
    malam/IR yang gelap & low-contrast; menaikkan kontras lokal sebelum
    inferensi terbukti membantu recall tanpa perlu re-training model."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if gray.mean() >= settings.LOW_LIGHT_BRIGHTNESS_THRESHOLD:
        return frame
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


class VehicleDetector:
    """Satu instance model YOLO dipakai bersama (shared) oleh semua worker
    stream supaya hemat VRAM. `model.track()` dari ultralytics sendiri
    thread-safe untuk inferensi berurutan, tapi kita tetap pakai lock
    supaya tidak ada race condition saat beberapa worker memanggil model
    yang sama secara bersamaan pada GPU yang sama.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or settings.MODEL_PATH
        self.device = _pick_device()
        self.half = self.device != "cpu"
        self.model = YOLO(self.model_path)
        self.model.to(self.device)
        logger.info("VehicleDetector: model=%s device=%s half=%s", self.model_path, self.device, self.half)
        self.infer_lock = threading.Lock()

    @classmethod
    def get_shared(cls, model_path: str | None = None) -> "VehicleDetector":
        """`model_path` cuma dipakai saat instance pertama kali dibuat
        (biasanya dipanggil sekali di startup dengan model pilihan user yang
        tersimpan). Panggilan berikutnya tanpa argumen akan mengembalikan
        instance yang sama."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(model_path)
        return cls._instance

    def reload(self, model_path: str):
        """Ganti model aktif tanpa restart backend. Karena semua kamera pakai
        instance shared yang sama, ganti di sini otomatis berlaku ke semua
        stream pada frame berikutnya."""
        with self.infer_lock:
            self.model = YOLO(model_path)
            self.model.to(self.device)
            self.model_path = model_path

    def track(self, frame, imgsz: int | None = None, persist: bool = True):
        """Jalankan deteksi + tracking (ByteTrack bawaan ultralytics) pada
        satu frame. Confidence filter per-kelas (+ bucket "tidak_diketahui")
        diterapkan di `tracker.py` setelah hasil mentah didapat -- di sini
        kita pakai `CONF_THRESHOLD_UNKNOWN` (nilai paling rendah) sebagai
        floor supaya deteksi borderline itu tidak sudah dibuang duluan oleh
        `model.track()` sebelum sempat di-bucket.
        """
        classes = list(settings.VEHICLE_CLASS_MAP.keys())
        frame_infer = _enhance_low_light(frame) if settings.ENABLE_LOW_LIGHT_ENHANCE else frame

        with self.infer_lock:
            results = self.model.track(
                frame_infer,
                imgsz=imgsz or settings.IMGSZ_DEFAULT,
                conf=settings.CONF_THRESHOLD_UNKNOWN,
                classes=classes,
                persist=persist,
                tracker="bytetrack.yaml",
                device=self.device,
                quantize=16 if self.half else None,
                verbose=False,
            )
        return results[0]
