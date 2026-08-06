"""Entrypoint FastAPI — Analitik Kamera (IndoVIS)."""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_cameras,
    routes_settings,
    routes_snapshot,
    routes_stats,
    routes_training,
    routes_ws,
    routes_zones,
)
from app.config import settings
from app.core import stream_worker
from app.core.detector import VehicleDetector
from app.db import store
from app.db.store import init_store

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Analitik Kamera - IndoVIS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_cameras.router)
app.include_router(routes_zones.router)
app.include_router(routes_snapshot.router)
app.include_router(routes_stats.router)
app.include_router(routes_settings.router)
app.include_router(routes_training.router)
app.include_router(routes_ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    init_store()

    # Muat pilihan model YOLO yang tersimpan (kalau ada & file-nya masih
    # ada di disk) supaya pilihan user dari sesi sebelumnya tetap kepakai
    # setelah backend restart. Detector shared harus diinisialisasi di sini
    # SEBELUM worker mulai jalan (worker.refresh_from_db() di bawah akan
    # memanggil VehicleDetector.get_shared() tanpa argumen dan dapat
    # instance yang sama).
    model_name = store.get_app_settings().get("model_name")
    model_path = None
    if model_name and (settings.MODELS_DIR / model_name).exists():
        model_path = str(settings.MODELS_DIR / model_name)
    VehicleDetector.get_shared(model_path)

    stream_worker.set_main_loop(asyncio.get_event_loop())
    stream_worker.worker_manager.refresh_from_db()


@app.on_event("shutdown")
def on_shutdown():
    stream_worker.worker_manager.shutdown_all()
