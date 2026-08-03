"""Endpoint statistik/agregat: total hari ini per kelas kendaraan (untuk
StatsSidebar), volume per jam (untuk VolumeChart), dan histori alert
(untuk AlertPanel saat pertama kali dimuat — update selanjutnya lewat
websocket)."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Alert, CountHistory
from app.db.session import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])

KELAS_LIST = ["motor", "mobil", "bus", "truk"]


@router.get("/summary")
def get_summary(camera_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Total kendaraan hari ini per kelas (agregat semua kamera atau 1 kamera)."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    query = db.query(CountHistory).filter(CountHistory.jam >= today_start)
    if camera_id is not None:
        query = query.filter(CountHistory.camera_id == camera_id)

    totals = defaultdict(int)
    for row in query.all():
        totals[row.kelas] += row.jumlah

    result = {kelas: totals.get(kelas, 0) for kelas in KELAS_LIST}
    result["total"] = sum(result.values())
    return result


@router.get("/volume")
def get_volume(camera_id: Optional[int] = None, hours: int = 24, db: Session = Depends(get_db)):
    """Volume kendaraan per jam, untuk grafik bar chart harian."""
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(CountHistory).filter(CountHistory.jam >= since)
    if camera_id is not None:
        query = query.filter(CountHistory.camera_id == camera_id)

    buckets: dict[datetime, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in query.all():
        buckets[row.jam][row.kelas] += row.jumlah

    result = []
    for jam in sorted(buckets.keys()):
        entry = {kelas: buckets[jam].get(kelas, 0) for kelas in KELAS_LIST}
        entry["jam"] = jam.strftime("%H:%M")
        entry["total"] = sum(entry[k] for k in KELAS_LIST)
        result.append(entry)

    return result


@router.get("/alerts")
def get_alerts(camera_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db)):
    """Histori alert (wrong-way / parkir liar / pelanggaran jalur) terbaru."""
    query = db.query(Alert).order_by(Alert.created_at.desc())
    if camera_id is not None:
        query = query.filter(Alert.camera_id == camera_id)

    rows = query.limit(limit).all()
    return [
        {
            "id": a.id,
            "camera_id": a.camera_id,
            "zone_id": a.zone_id,
            "tipe": a.tipe,
            "track_id": a.track_id,
            "pesan": a.pesan,
            "created_at": a.created_at,
        }
        for a in rows
    ]
