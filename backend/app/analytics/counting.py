"""Counting kendaraan per kelas (motor/mobil/bus/truk) berdasarkan zona
bertipe 'counting'. Satu track_id dihitung sekali per zona (saat pertama
kali centroid-nya terdeteksi di dalam poligon zona tsb)."""
from dataclasses import dataclass

from app.core.state import CameraState
from app.core.tracker import Detection
from app.core.zones import RuntimeZone, point_in_polygon, zones_by_type


@dataclass
class CountEvent:
    zone_id: int
    track_id: int
    kelas: str


def process(detections: list[Detection], zones: list[RuntimeZone], state: CameraState) -> list[CountEvent]:
    events: list[CountEvent] = []
    counting_zones = zones_by_type(zones, "counting")
    if not counting_zones:
        return events

    for det in detections:
        for zone in counting_zones:
            already = state.counted_in_zone[zone.id]
            if det.track_id in already:
                continue
            if point_in_polygon(det.centroid, zone.koordinat):
                already.add(det.track_id)
                events.append(CountEvent(zone_id=zone.id, track_id=det.track_id, kelas=det.class_name))

    return events
