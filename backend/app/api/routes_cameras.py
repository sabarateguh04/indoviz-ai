"""CRUD kamera (tambah/edit/hapus RTSP URL) + endpoint test koneksi.

Menambah/mengedit/menghapus kamera di sini langsung memicu start/stop
worker terkait (`stream_worker.worker_manager`) — backend TIDAK perlu
di-restart supaya kamera baru langsung mulai diproses.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.rtsp_utils import test_connection
from app.core.stream_worker import worker_manager
from app.db.models import Camera
from app.db.session import get_db

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


class SpeedCalibration(BaseModel):
    pixel_points: list[list[float]]
    distance_m: float


class CameraCreate(BaseModel):
    nama: str
    rtsp_url: str
    imgsz: Optional[int] = None
    speed_calibration: Optional[SpeedCalibration] = None
    active: bool = True


class CameraUpdate(BaseModel):
    nama: Optional[str] = None
    rtsp_url: Optional[str] = None
    imgsz: Optional[int] = None
    speed_calibration: Optional[SpeedCalibration] = None
    active: Optional[bool] = None


class TestConnectionRequest(BaseModel):
    rtsp_url: str


class CameraOut(BaseModel):
    id: int
    nama: str
    rtsp_url: str
    status: str
    active: bool
    imgsz: Optional[int] = None
    speed_calibration: Optional[dict] = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    return camera


@router.post("/test-connection")
def test_camera_connection(payload: TestConnectionRequest):
    berhasil, pesan = test_connection(payload.rtsp_url)
    return {"berhasil": berhasil, "pesan": pesan}


@router.post("", response_model=CameraOut)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    camera = Camera(
        nama=payload.nama,
        rtsp_url=payload.rtsp_url,
        imgsz=payload.imgsz,
        speed_calibration=payload.speed_calibration.model_dump() if payload.speed_calibration else None,
        active=payload.active,
        status="offline",
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    if camera.active:
        worker_manager.start_camera(camera.id)

    return camera


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    rtsp_changed = payload.rtsp_url is not None and payload.rtsp_url != camera.rtsp_url

    if payload.nama is not None:
        camera.nama = payload.nama
    if payload.rtsp_url is not None:
        camera.rtsp_url = payload.rtsp_url
    if payload.imgsz is not None:
        camera.imgsz = payload.imgsz
    if payload.speed_calibration is not None:
        camera.speed_calibration = payload.speed_calibration.model_dump()
    if payload.active is not None:
        camera.active = payload.active

    db.commit()
    db.refresh(camera)

    if camera.active and (rtsp_changed or payload.active is True):
        worker_manager.restart_camera(camera.id)
    elif not camera.active:
        worker_manager.stop_camera(camera.id)

    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    worker_manager.stop_camera(camera_id)
    db.delete(camera)
    db.commit()
    return {"ok": True}
