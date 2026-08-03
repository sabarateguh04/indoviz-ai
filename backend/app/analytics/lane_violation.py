"""Deteksi pelanggaran jalur — begitu sebuah track pertama kali teridentifikasi
berada di salah satu zona bertipe 'lane', jalur itu jadi "jalur seharusnya".
Kalau centroid track tsb kemudian keluar dari poligon jalur tersebut
(pindah ke jalur lain atau keluar area jalur), maka dianggap pelanggaran.
"""
from dataclasses import dataclass

from app.core.state import CameraState
from app.core.tracker import Detection
from app.core.zones import RuntimeZone, point_in_polygon, zones_by_type


@dataclass
class LaneViolationEvent:
    zone_id: int  # jalur asal (seharusnya)
    track_id: int
    kelas: str


def process(detections: list[Detection], zones: list[RuntimeZone], state: CameraState) -> list[LaneViolationEvent]:
    events: list[LaneViolationEvent] = []
    lane_zones = zones_by_type(zones, "lane")
    if not lane_zones:
        return events

    for det in detections:
        current_zone = next((z for z in lane_zones if point_in_polygon(det.centroid, z.koordinat)), None)

        home_zone_id = state.track_home_lane.get(det.track_id)

        if home_zone_id is None:
            if current_zone is not None:
                state.track_home_lane[det.track_id] = current_zone.id
            continue

        still_in_home_lane = current_zone is not None and current_zone.id == home_zone_id
        if still_in_home_lane:
            continue

        if det.track_id in state.lane_violation_alerted:
            continue

        state.lane_violation_alerted.add(det.track_id)
        events.append(LaneViolationEvent(zone_id=home_zone_id, track_id=det.track_id, kelas=det.class_name))

    return events
