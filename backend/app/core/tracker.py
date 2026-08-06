"""Konversi hasil `model.track()` ultralytics jadi struktur deteksi yang
dipakai bersama oleh semua modul di `analytics/` (bbox, track_id, class,
centroid, confidence per frame).

ByteTrack (via ultralytics) dipakai supaya track_id konsisten antar frame —
semua fitur analitik lanjutan (speed, wrong-way, illegal parking, dsb)
butuh ID ini, bukan cuma deteksi per-frame.
"""
from dataclasses import dataclass

from app.config import settings


@dataclass
class Detection:
    track_id: int
    class_id: int
    class_name: str
    conf: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (piksel)
    centroid: tuple[float, float]


def _conf_threshold_for(class_id: int) -> float:
    if class_id == settings.MOTOR_CLASS_ID:
        return settings.CONF_THRESHOLD_MOTOR
    return settings.CONF_THRESHOLD_DEFAULT


def extract_detections(result) -> list[Detection]:
    """Terima 1 objek `Results` dari ultralytics, kembalikan list Detection
    yang sudah difilter pakai confidence threshold per-kelas dan hanya
    untuk box yang punya track_id (artinya sudah lolos tracker)."""
    detections: list[Detection] = []

    boxes = result.boxes
    if boxes is None or boxes.id is None:
        return detections

    xyxy = boxes.xyxy.cpu().numpy()
    track_ids = boxes.id.cpu().numpy().astype(int)
    class_ids = boxes.cls.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()

    for i in range(len(track_ids)):
        class_id = int(class_ids[i])
        conf = float(confs[i])
        if class_id not in settings.VEHICLE_CLASS_MAP:
            continue
        if conf < settings.CONF_THRESHOLD_UNKNOWN:
            continue

        # Lolos threshold per-kelas (mis. motor >=0.25, mobil/bus/truk
        # >=0.4) -> dipakai nama kelas aslinya. Di bawah itu tapi masih
        # >= CONF_THRESHOLD_UNKNOWN -> model cukup yakin "ada objek" tapi
        # tidak cukup yakin jenisnya (umum terjadi di footage malam/IR
        # kontras rendah) -> tetap dihitung, dilabel "tidak_diketahui"
        # daripada dibuang begitu saja.
        if conf >= _conf_threshold_for(class_id):
            class_name = settings.VEHICLE_CLASS_MAP[class_id]
        else:
            class_name = settings.UNKNOWN_CLASS_NAME

        x1, y1, x2, y2 = (float(v) for v in xyxy[i])
        centroid = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

        detections.append(
            Detection(
                track_id=int(track_ids[i]),
                class_id=class_id,
                class_name=class_name,
                conf=conf,
                bbox=(x1, y1, x2, y2),
                centroid=centroid,
            )
        )

    return detections
