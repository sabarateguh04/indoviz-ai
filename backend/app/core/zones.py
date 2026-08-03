"""Util poligon zona (counting / larangan parkir / arah / jalur).

Tidak pakai library eksternal (shapely dkk) supaya dependency backend tetap
ringan — cukup ray-casting sederhana untuk point-in-polygon.
"""
import math
from dataclasses import dataclass

Point = tuple[float, float]


@dataclass
class RuntimeZone:
    id: int
    camera_id: int
    nama: str
    tipe_zona: str
    koordinat: list[Point]
    arah_normal_deg: float | None = None


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    """Ray-casting algorithm standar. `polygon` minimal 3 titik."""
    if len(polygon) < 3:
        return False

    x, y = point
    inside = False
    n = len(polygon)
    x1, y1 = polygon[0]
    for i in range(1, n + 1):
        x2, y2 = polygon[i % n]
        if y > min(y1, y2):
            if y <= max(y1, y2):
                if x <= max(x1, x2):
                    if y1 != y2:
                        x_intersect = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                    else:
                        x_intersect = x1
                    if x1 == x2 or x <= x_intersect:
                        inside = not inside
        x1, y1 = x2, y2
    return inside


def polygon_centroid(polygon: list[Point]) -> Point:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def vector_angle_deg(p_from: Point, p_to: Point) -> float:
    """Sudut vektor gerak (derajat, 0-360) dari p_from ke p_to. 0 derajat
    mengarah ke +x (kanan), berlawanan jarum jam sesuai konvensi matematika
    standar (catatan: sumbu y gambar mengarah ke bawah, jadi visualnya
    searah jarum jam)."""
    dx = p_to[0] - p_from[0]
    dy = p_to[1] - p_from[1]
    angle = math.degrees(math.atan2(dy, dx))
    return angle % 360


def angle_difference_deg(a: float, b: float) -> float:
    """Selisih sudut terpendek antara dua sudut (0-180 derajat)."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def zones_by_type(zones: list[RuntimeZone], tipe: str) -> list[RuntimeZone]:
    return [z for z in zones if z.tipe_zona == tipe]
