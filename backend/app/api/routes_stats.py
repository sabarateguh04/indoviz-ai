"""Endpoint statistik/agregat: total hari ini per kelas kendaraan (untuk
StatsSidebar), volume per jam (untuk VolumeChart), dan histori alert
(untuk AlertPanel saat pertama kali dimuat — update selanjutnya lewat
websocket). Data dibaca dari file JSON per tanggal (`app/db/store.py`)."""
from typing import Optional

from fastapi import APIRouter

from app.db import store

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def get_summary(camera_id: Optional[int] = None):
    """Total kendaraan hari ini per kelas (agregat semua kamera atau 1 kamera)."""
    return store.get_summary(camera_id)


@router.get("/volume")
def get_volume(camera_id: Optional[int] = None, hours: int = 24):
    """Volume kendaraan per jam, untuk grafik bar chart harian."""
    return store.get_volume(camera_id, hours)


@router.get("/alerts")
def get_alerts(camera_id: Optional[int] = None, limit: int = 50):
    """Histori alert (wrong-way / parkir liar / pelanggaran jalur) terbaru."""
    return store.get_alerts(camera_id, limit)
