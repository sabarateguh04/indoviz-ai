"""Ambil 1 frame terbaru dari RTSP kamera tertentu, dipakai sebagai gambar
background di `ZoneEditor.jsx` (frontend) untuk menggambar poligon zona."""
import cv2
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.rtsp_utils import capture_snapshot
from app.db.models import Camera
from app.db.session import get_db

router = APIRouter(prefix="/api/snapshot", tags=["snapshot"])


@router.get("/{camera_id}")
def get_snapshot(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frame = capture_snapshot(camera.rtsp_url)
    if frame is None:
        raise HTTPException(status_code=503, detail="Gagal mengambil frame dari RTSP kamera ini")

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="Gagal encode snapshot ke JPEG")

    return Response(content=buf.tobytes(), media_type="image/jpeg")
