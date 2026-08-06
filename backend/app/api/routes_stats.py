"""Endpoint statistik/agregat: total per kelas kendaraan (untuk
StatsSidebar), volume per jam (untuk VolumeChart), dan histori alert
(untuk AlertPanel saat pertama kali dimuat — update selanjutnya lewat
websocket). Data dibaca dari file JSON per tanggal (`app/db/store.py`).

Semua endpoint menerima filter opsional `date` (YYYY-MM-DD, default hari
ini/N jam terakhir) dan `zone_type` (counting/no_parking/direction/lane)
supaya frontend bisa breakdown per tanggal & per tipe zona."""
from typing import Optional

from fastapi import APIRouter

from app.db import store

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def get_summary(camera_id: Optional[int] = None, date: Optional[str] = None, zone_type: Optional[str] = None):
    """Total kendaraan per kelas (default hari ini, atau tanggal tertentu),
    agregat semua kamera atau 1 kamera, opsional per tipe zona."""
    return store.get_summary(camera_id, date, zone_type)


@router.get("/volume")
def get_volume(
    camera_id: Optional[int] = None,
    hours: int = 24,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
):
    """Volume kendaraan per jam, untuk grafik bar chart. Kalau `date` diisi,
    dipakai 1 hari penuh itu dan `hours` diabaikan."""
    return store.get_volume(camera_id, hours, date, zone_type)


@router.get("/alerts")
def get_alerts(
    camera_id: Optional[int] = None,
    limit: int = 50,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
):
    """Histori alert (wrong-way / parkir liar / pelanggaran jalur) terbaru,
    opsional difilter per tanggal & tipe zona."""
    return store.get_alerts(camera_id, limit, date, zone_type)
