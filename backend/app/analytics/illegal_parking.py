"""Deteksi parkir liar / berhenti di zona larangan — objek yang diam
(delta posisi < threshold) di dalam poligon zona 'no_parking' selama lebih
dari N detik akan memicu alert (sekali per track, tidak diulang tiap frame).
"""
import math
import time
from dataclasses import dataclass

from app.config import settings
from app.core.state import CameraState
from app.core.tracker import Detection
from app.core.zones import RuntimeZone, point_in_polygon, zones_by_type


@dataclass
class IllegalParkingEvent:
    zone_id: int
    track_id: int
    kelas: str
    durasi_detik: float


def process(
    detections: list[Detection],
    zones: list[RuntimeZone],
    state: CameraState,
    frame_shape: tuple[int, int],
) -> list[IllegalParkingEvent]:
    events: list[IllegalParkingEvent] = []
    no_parking_zones = zones_by_type(zones, "no_parking")
    if not no_parking_zones:
        return events

    height, width = frame_shape[:2]
    diagonal = math.hypot(width, height)
    move_threshold_px = settings.ILLEGAL_PARKING_MOVE_THRESHOLD * diagonal

    now = time.time()
    seen_in_zone: set[int] = set()

    for det in detections:
        zone = next((z for z in no_parking_zones if point_in_polygon(det.centroid, z.koordinat)), None)
        if zone is None:
            continue

        seen_in_zone.add(det.track_id)
        anchor = state.stationary_anchor.get(det.track_id)

        if anchor is None:
            state.stationary_anchor[det.track_id] = det.centroid
            state.stationary_since[det.track_id] = now
            continue

        moved = math.hypot(det.centroid[0] - anchor[0], det.centroid[1] - anchor[1])
        if moved > move_threshold_px:
            # Objek bergerak cukup jauh — reset acuan diam.
            state.stationary_anchor[det.track_id] = det.centroid
            state.stationary_since[det.track_id] = now
            state.illegal_parking_alerted.discard(det.track_id)
            continue

        duration = now - state.stationary_since[det.track_id]
        if duration >= settings.ILLEGAL_PARKING_SECONDS and det.track_id not in state.illegal_parking_alerted:
            state.illegal_parking_alerted.add(det.track_id)
            events.append(
                IllegalParkingEvent(
                    zone_id=zone.id,
                    track_id=det.track_id,
                    kelas=det.class_name,
                    durasi_detik=round(duration, 1),
                )
            )

    # Track yang tidak lagi berada di zona larangan manapun -> reset state
    # diamnya supaya kalau berhenti lagi nanti dihitung dari awal.
    stale_ids = [tid for tid in state.stationary_anchor if tid not in seen_in_zone]
    for tid in stale_ids:
        state.stationary_anchor.pop(tid, None)
        state.stationary_since.pop(tid, None)
        state.illegal_parking_alerted.discard(tid)

    return events
