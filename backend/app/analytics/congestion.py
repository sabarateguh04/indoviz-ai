"""Estimasi tingkat kepadatan/kemacetan per zona — hitung jumlah objek per
zona (rata-rata bergerak selama `CONGESTION_INTERVAL_SECONDS`), lalu
klasifikasikan level: lengang / padat / macet berdasarkan threshold di
config.
"""
import time
from dataclasses import dataclass

from app.config import settings
from app.core.state import CameraState
from app.core.tracker import Detection
from app.core.zones import RuntimeZone, point_in_polygon, zones_by_type


@dataclass
class CongestionStatus:
    zone_id: int
    jumlah_saat_ini: int
    rata_rata: float
    level: str  # lengang | padat | macet


def _classify(avg_count: float) -> str:
    if avg_count >= settings.CONGESTION_MACET_THRESHOLD:
        return "macet"
    if avg_count >= settings.CONGESTION_PADAT_THRESHOLD:
        return "padat"
    return "lengang"


def process(detections: list[Detection], zones: list[RuntimeZone], state: CameraState) -> list[CongestionStatus]:
    results: list[CongestionStatus] = []
    counting_zones = zones_by_type(zones, "counting")
    if not counting_zones:
        return results

    now = time.time()
    window_start = now - settings.CONGESTION_INTERVAL_SECONDS

    for zone in counting_zones:
        current_count = sum(1 for det in detections if point_in_polygon(det.centroid, zone.koordinat))

        samples = state.zone_count_samples[zone.id]
        samples.append((now, current_count))
        while samples and samples[0][0] < window_start:
            samples.popleft()

        avg_count = sum(c for _, c in samples) / len(samples) if samples else 0.0

        results.append(
            CongestionStatus(
                zone_id=zone.id,
                jumlah_saat_ini=current_count,
                rata_rata=round(avg_count, 1),
                level=_classify(avg_count),
            )
        )

    return results
