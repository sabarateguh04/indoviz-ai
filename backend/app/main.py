"""Entrypoint FastAPI — Analitik Kamera (IndoVIS)."""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_cameras, routes_snapshot, routes_stats, routes_ws, routes_zones
from app.core import stream_worker
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
app.include_router(routes_ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    init_store()
    stream_worker.set_main_loop(asyncio.get_event_loop())
    stream_worker.worker_manager.refresh_from_db()


@app.on_event("shutdown")
def on_shutdown():
    stream_worker.worker_manager.shutdown_all()
