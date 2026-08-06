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


class DisplayUpdate(BaseModel):
    ws_broadcast_interval: float


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


@router.get("/display")
def get_display_settings():
    """Interval broadcast frame ke frontend (detik) -- makin kecil makin
    smooth live view-nya, tapi makin besar juga bandwidth/CPU per kamera.
    Ini KOSMETIK doang (kecepatan tampilan), TIDAK mempengaruhi kecepatan
    deteksi/counting -- itu jalan di frame rate penuh terlepas dari nilai
    ini, lihat core/stream_worker.py."""
    interval = store.get_app_settings().get("ws_broadcast_interval") or settings.WS_BROADCAST_INTERVAL
    return {
        "ws_broadcast_interval": interval,
        "min": settings.WS_BROADCAST_INTERVAL_MIN,
        "max": settings.WS_BROADCAST_INTERVAL_MAX,
    }


@router.put("/display")
def set_display_settings(payload: DisplayUpdate):
    if not (settings.WS_BROADCAST_INTERVAL_MIN <= payload.ws_broadcast_interval <= settings.WS_BROADCAST_INTERVAL_MAX):
        raise HTTPException(
            status_code=400,
            detail=f"ws_broadcast_interval harus antara {settings.WS_BROADCAST_INTERVAL_MIN} "
                   f"dan {settings.WS_BROADCAST_INTERVAL_MAX} detik",
        )
    store.update_app_settings({"ws_broadcast_interval": payload.ws_broadcast_interval})
    # Semua StreamWorker baca ulang nilai ini tiap ZONE_REFRESH_INTERVAL
    # (5 detik) -- lihat core/stream_worker.py -- jadi berlaku tanpa restart,
    # cuma butuh beberapa detik.
    return {"ws_broadcast_interval": payload.ws_broadcast_interval}
