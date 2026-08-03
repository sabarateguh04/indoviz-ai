"""Ambil 1 frame terbaru dari RTSP kamera tertentu, dipakai sebagai gambar
background di `ZoneEditor.jsx` (frontend) untuk menggambar poligon zona."""
import cv2
from fastapi import APIRouter, HTTPException, Response

from app.core.rtsp_utils import capture_snapshot
from app.db import store

router = APIRouter(prefix="/api/snapshot", tags=["snapshot"])


@router.get("/{camera_id}")
def get_snapshot(camera_id: int):
    camera = store.get_camera(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frame = capture_snapshot(camera.rtsp_url)
    if frame is None:
        raise HTTPException(status_code=503, detail="Gagal mengambil frame dari RTSP kamera ini")

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="Gagal encode snapshot ke JPEG")

    return Response(content=buf.tobytes(), media_type="image/jpeg")
