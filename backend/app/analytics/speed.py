"""Estimasi kecepatan kendaraan dari perpindahan centroid antar frame,
dikonversi piksel->meter pakai kalibrasi per-kamera (2 titik referensi
piksel + jarak nyata dalam meter antara keduanya).

Tanpa kalibrasi, kecepatan tidak bisa dihitung (return None) — jangan
menebak skala.
"""
import math

from app.core.state import CameraState
from app.core.tracker import Detection


def _pixels_per_meter(speed_calibration: dict | None) -> float | None:
    if not speed_calibration:
        return None
    points = speed_calibration.get("pixel_points")
    distance_m = speed_calibration.get("distance_m")
    if not points or len(points) != 2 or not distance_m:
        return None

    (x1, y1), (x2, y2) = points
    pixel_dist = math.hypot(x2 - x1, y2 - y1)
    if pixel_dist == 0:
        return None
    return pixel_dist / distance_m


def process(detections: list[Detection], state: CameraState, speed_calibration: dict | None) -> dict[int, float]:
    """Return dict track_id -> kecepatan (km/h). Track tanpa histori cukup
    atau tanpa kalibrasi kamera tidak dimasukkan ke hasil."""
    speeds: dict[int, float] = {}

    px_per_m = _pixels_per_meter(speed_calibration)
    if px_per_m is None:
        return speeds

    for det in detections:
        history = state.track_history.get(det.track_id)
        if not history or len(history) < 2:
            continue

        t_prev, p_prev = history[-2]
        t_now, p_now = history[-1]
        dt = t_now - t_prev
        if dt <= 0:
            continue

        pixel_dist = math.hypot(p_now[0] - p_prev[0], p_now[1] - p_prev[1])
        meters = pixel_dist / px_per_m
        speed_m_s = meters / dt
        speeds[det.track_id] = round(speed_m_s * 3.6, 1)  # km/h

    return speeds
