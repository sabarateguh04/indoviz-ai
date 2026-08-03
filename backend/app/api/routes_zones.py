"""CRUD poligon zona per kamera (counting/no-parking/arah/jalur).

Poligon disimpan sebagai list koordinat [x, y] relatif ke resolusi frame
asli kamera (piksel). `stream_worker.py` membaca ulang zona dari sini
secara berkala, jadi perubahan di sini otomatis kepakai tanpa restart
backend.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.db import store

router = APIRouter(prefix="/api/zones", tags=["zones"])

TIPE_ZONA_VALID = {"counting", "no_parking", "direction", "lane"}


class ZoneCreate(BaseModel):
    camera_id: int
    nama: str = ""
    tipe_zona: str
    koordinat: list[list[float]]
    arah_normal_deg: Optional[float] = None

    @field_validator("tipe_zona")
    @classmethod
    def validate_tipe(cls, v):
        if v not in TIPE_ZONA_VALID:
            raise ValueError(f"tipe_zona harus salah satu dari {sorted(TIPE_ZONA_VALID)}")
        return v

    @field_validator("koordinat")
    @classmethod
    def validate_koordinat(cls, v):
        if len(v) < 3:
            raise ValueError("Poligon zona minimal harus punya 3 titik")
        return v


class ZoneUpdate(BaseModel):
    nama: Optional[str] = None
    tipe_zona: Optional[str] = None
    koordinat: Optional[list[list[float]]] = None
    arah_normal_deg: Optional[float] = None

    @field_validator("tipe_zona")
    @classmethod
    def validate_tipe(cls, v):
        if v is not None and v not in TIPE_ZONA_VALID:
            raise ValueError(f"tipe_zona harus salah satu dari {sorted(TIPE_ZONA_VALID)}")
        return v

    @field_validator("koordinat")
    @classmethod
    def validate_koordinat(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError("Poligon zona minimal harus punya 3 titik")
        return v


class ZoneOut(BaseModel):
    id: int
    camera_id: int
    nama: str
    tipe_zona: str
    koordinat: list[list[float]]
    arah_normal_deg: Optional[float] = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[ZoneOut])
def list_zones(camera_id: Optional[int] = None):
    return store.list_zones(camera_id)


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int):
    zone = store.get_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zona tidak ditemukan")
    return zone


@router.post("", response_model=ZoneOut)
def create_zone(payload: ZoneCreate):
    return store.create_zone(
        {
            "camera_id": payload.camera_id,
            "nama": payload.nama,
            "tipe_zona": payload.tipe_zona,
            "koordinat": payload.koordinat,
            "arah_normal_deg": payload.arah_normal_deg,
        }
    )


@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, payload: ZoneUpdate):
    zone = store.update_zone(
        zone_id,
        {
            "nama": payload.nama,
            "tipe_zona": payload.tipe_zona,
            "koordinat": payload.koordinat,
            "arah_normal_deg": payload.arah_normal_deg,
        },
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zona tidak ditemukan")
    return zone


@router.delete("/{zone_id}")
def delete_zone(zone_id: int):
    if not store.delete_zone(zone_id):
        raise HTTPException(status_code=404, detail="Zona tidak ditemukan")
    return {"ok": True}
