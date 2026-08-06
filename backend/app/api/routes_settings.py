"""Endpoint pengaturan aplikasi — saat ini baru pilihan model YOLO aktif.

Model yang dipilih user disimpan di app/data/settings.json (lihat
app/db/store.py) supaya tetap kepakai setelah backend di-restart, dan
diterapkan langsung ke semua kamera tanpa restart lewat
`VehicleDetector.reload()` (semua worker stream pakai instance model yang
sama / shared, lihat core/detector.py)."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.core.detector import VehicleDetector
from app.db import store

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelUpdate(BaseModel):
    model_name: str


def _available_models() -> list[str]:
    """Model .pt yang benar-benar ada di MODELS_DIR — bukan cuma daftar
    hardcode di config — supaya dropdown di frontend tidak menawarkan model
    yang belum di-download ke server."""
    if not settings.MODELS_DIR.exists():
        return []
    return sorted(p.name for p in settings.MODELS_DIR.glob("*.pt"))


@router.get("/model")
def get_model_settings():
    detector = VehicleDetector.get_shared()
    return {
        "current": Path(detector.model_path).name,
        "available": _available_models(),
    }


@router.put("/model")
def set_model(payload: ModelUpdate):
    available = _available_models()
    if payload.model_name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{payload.model_name}' tidak ditemukan di {settings.MODELS_DIR}",
        )

    model_path = str(settings.MODELS_DIR / payload.model_name)
    detector = VehicleDetector.get_shared()
    try:
        detector.reload(model_path)
    except Exception as exc:  # file .pt korup/tidak kompatibel, dsb.
        raise HTTPException(status_code=400, detail=f"Gagal memuat model: {exc}") from exc

    store.update_app_settings({"model_name": payload.model_name})
    return {"current": payload.model_name, "available": available}
