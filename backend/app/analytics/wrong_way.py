"""Deteksi kendaraan melawan arah — bandingkan vektor arah gerak tracked
object dengan arah normal yang ditandai user pada zona bertipe 'direction'.
"""
from dataclasses import dataclass

from app.config import settings
from app.core.state import CameraState
from app.core.tracker import Detection
from app.core.zones import (
    RuntimeZone,
    angle_difference_deg,
    point_in_polygon,
    vector_angle_deg,
    zones_by_type,
)


@dataclass
class WrongWayEvent:
    zone_id: int
    track_id: int
    kelas: str
    sudut_gerak: float
    sudut_normal: float


def process(detections: list[Detection], zones: list[RuntimeZone], state: CameraState) -> list[WrongWayEvent]:
    events: list[WrongWayEvent] = []
    direction_zones = zones_by_type(zones, "direction")
    if not direction_zones:
        return events

    for det in detections:
        history = state.track_history.get(det.track_id)
        if not history or len(history) < 2:
            continue

        _, p_prev = history[-2]
        _, p_now = history[-1]
        # Kalau objek nyaris tidak bergerak, arah tidak bisa dipercaya — skip.
        if (p_now[0] - p_prev[0]) ** 2 + (p_now[1] - p_prev[1]) ** 2 < 4:
            continue

        movement_angle = vector_angle_deg(p_prev, p_now)

        for zone in direction_zones:
            if zone.arah_normal_deg is None:
                continue
            if not point_in_polygon(det.centroid, zone.koordinat):
                continue

            diff = angle_difference_deg(movement_angle, zone.arah_normal_deg)
            if diff >= settings.WRONG_WAY_ANGLE_THRESHOLD:
                if det.track_id in state.wrong_way_alerted:
                    continue
                state.wrong_way_alerted.add(det.track_id)
                events.append(
                    WrongWayEvent(
                        zone_id=zone.id,
                        track_id=det.track_id,
                        kelas=det.class_name,
                        sudut_gerak=round(movement_angle, 1),
                        sudut_normal=zone.arah_normal_deg,
                    )
                )

    return events
