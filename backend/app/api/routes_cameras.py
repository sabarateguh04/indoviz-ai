"""CRUD kamera (tambah/edit/hapus RTSP URL) + endpoint test koneksi.

Menambah/mengedit/menghapus kamera di sini langsung memicu start/stop
worker terkait (`stream_worker.worker_manager`) — backend TIDAK perlu
di-restart supaya kamera baru langsung mulai diproses.

Data kamera disimpan sebagai file JSON (`app/db/store.py`), bukan SQL.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.rtsp_utils import test_connection
from app.core.stream_worker import worker_manager
from app.db import store

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
def list_cameras():
    return store.list_cameras()


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int):
    camera = store.get_camera(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    return camera


@router.post("/test-connection")
def test_camera_connection(payload: TestConnectionRequest):
    berhasil, pesan = test_connection(payload.rtsp_url)
    return {"berhasil": berhasil, "pesan": pesan}


@router.post("", response_model=CameraOut)
def create_camera(payload: CameraCreate):
    camera = store.create_camera(
        {
            "nama": payload.nama,
            "rtsp_url": payload.rtsp_url,
            "imgsz": payload.imgsz,
            "speed_calibration": payload.speed_calibration.model_dump() if payload.speed_calibration else None,
            "active": payload.active,
        }
    )

    if camera.active:
        worker_manager.start_camera(camera.id)

    return camera


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, payload: CameraUpdate):
    existing = store.get_camera(camera_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    rtsp_changed = payload.rtsp_url is not None and payload.rtsp_url != existing.rtsp_url

    camera = store.update_camera(
        camera_id,
        {
            "nama": payload.nama,
            "rtsp_url": payload.rtsp_url,
            "imgsz": payload.imgsz,
            "speed_calibration": payload.speed_calibration.model_dump() if payload.speed_calibration else None,
            "active": payload.active,
        },
    )

    if camera.active and (rtsp_changed or payload.active is True):
        worker_manager.restart_camera(camera.id)
    elif not camera.active:
        worker_manager.stop_camera(camera.id)

    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: int):
    existing = store.get_camera(camera_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    worker_manager.stop_camera(camera_id)
    store.delete_camera(camera_id)
    return {"ok": True}
