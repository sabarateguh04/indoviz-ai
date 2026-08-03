"""Penyimpanan data berbasis file JSON — tidak pakai SQLite/PostgreSQL.

Dipisah per kategori dan per tanggal supaya tiap file tetap kecil/ringan:

    app/data/
      cameras.json             -> daftar kamera (kategori, jarang berubah)
      zones.json               -> daftar zona (kategori, jarang berubah)
      counts/YYYY-MM-DD.jsonl  -> event counting per hari (append-only)
      alerts/YYYY-MM-DD.jsonl  -> event alert per hari (append-only)

`cameras.json`/`zones.json` ditulis ulang penuh tiap CRUD (ukurannya kecil,
jumlah kamera/zona wajar). `counts`/`alerts` pakai format JSONL (1 baris =
1 event) dan di-append per hari supaya tidak perlu baca+tulis ulang seluruh
histori tiap kali ada event baru.

Satu lock global dipakai untuk semua operasi baca/tulis — cukup aman dan
sederhana untuk skala target (8-15 stream), karena tiap event (counting/
alert) jarang terjadi dibanding jumlah frame yang diproses.
"""
import datetime
import json
import threading
from pathlib import Path
from typing import Optional

from app.config import settings
from app.db.models import Camera, Zone

_lock = threading.RLock()

DATA_DIR = settings.DATA_DIR
CAMERAS_FILE = DATA_DIR / "cameras.json"
ZONES_FILE = DATA_DIR / "zones.json"
COUNTS_DIR = DATA_DIR / "counts"
ALERTS_DIR = DATA_DIR / "alerts"

KELAS_LIST = ["motor", "mobil", "bus", "truk"]

_EMPTY = {"next_id": 1, "items": []}


def init_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COUNTS_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    if not CAMERAS_FILE.exists():
        _write_json(CAMERAS_FILE, dict(_EMPTY))
    if not ZONES_FILE.exists():
        _write_json(ZONES_FILE, dict(_EMPTY))


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(default)


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)  # ganti atomik, hindari file korup kalau proses mati di tengah tulis


# ==================== Kamera ====================

def list_cameras() -> list[Camera]:
    with _lock:
        data = _read_json(CAMERAS_FILE, _EMPTY)
    return [Camera.from_dict(d) for d in data["items"]]


def list_active_cameras() -> list[Camera]:
    return [c for c in list_cameras() if c.active]


def get_camera(camera_id: int) -> Optional[Camera]:
    for c in list_cameras():
        if c.id == camera_id:
            return c
    return None


def create_camera(payload: dict) -> Camera:
    with _lock:
        data = _read_json(CAMERAS_FILE, _EMPTY)
        camera = Camera(
            id=data["next_id"],
            nama=payload["nama"],
            rtsp_url=payload["rtsp_url"],
            status="offline",
            active=payload.get("active", True),
            imgsz=payload.get("imgsz"),
            speed_calibration=payload.get("speed_calibration"),
        )
        data["items"].append(camera.to_dict())
        data["next_id"] += 1
        _write_json(CAMERAS_FILE, data)
        return camera


def update_camera(camera_id: int, changes: dict) -> Optional[Camera]:
    with _lock:
        data = _read_json(CAMERAS_FILE, _EMPTY)
        for item in data["items"]:
            if item["id"] == camera_id:
                item.update({k: v for k, v in changes.items() if v is not None})
                _write_json(CAMERAS_FILE, data)
                return Camera.from_dict(item)
    return None


def set_camera_status(camera_id: int, status: str):
    """Dipanggil tiap frame oleh stream_worker — hanya menulis file kalau
    status benar-benar berubah, supaya tidak menulis ulang JSON tiap frame."""
    with _lock:
        data = _read_json(CAMERAS_FILE, _EMPTY)
        changed = False
        for item in data["items"]:
            if item["id"] == camera_id and item.get("status") != status:
                item["status"] = status
                changed = True
        if changed:
            _write_json(CAMERAS_FILE, data)


def delete_camera(camera_id: int) -> bool:
    with _lock:
        data = _read_json(CAMERAS_FILE, _EMPTY)
        before = len(data["items"])
        data["items"] = [it for it in data["items"] if it["id"] != camera_id]
        if len(data["items"]) == before:
            return False
        _write_json(CAMERAS_FILE, data)

        zdata = _read_json(ZONES_FILE, _EMPTY)
        zdata["items"] = [z for z in zdata["items"] if z["camera_id"] != camera_id]
        _write_json(ZONES_FILE, zdata)
    return True


# ==================== Zona ====================

def list_zones(camera_id: Optional[int] = None) -> list[Zone]:
    with _lock:
        data = _read_json(ZONES_FILE, _EMPTY)
    zones = [Zone.from_dict(d) for d in data["items"]]
    if camera_id is not None:
        zones = [z for z in zones if z.camera_id == camera_id]
    return zones


def get_zone(zone_id: int) -> Optional[Zone]:
    for z in list_zones():
        if z.id == zone_id:
            return z
    return None


def create_zone(payload: dict) -> Zone:
    with _lock:
        data = _read_json(ZONES_FILE, _EMPTY)
        zone = Zone(
            id=data["next_id"],
            camera_id=payload["camera_id"],
            nama=payload.get("nama", ""),
            tipe_zona=payload["tipe_zona"],
            koordinat=payload["koordinat"],
            arah_normal_deg=payload.get("arah_normal_deg"),
        )
        data["items"].append(zone.to_dict())
        data["next_id"] += 1
        _write_json(ZONES_FILE, data)
        return zone


def update_zone(zone_id: int, changes: dict) -> Optional[Zone]:
    with _lock:
        data = _read_json(ZONES_FILE, _EMPTY)
        for item in data["items"]:
            if item["id"] == zone_id:
                item.update({k: v for k, v in changes.items() if v is not None})
                _write_json(ZONES_FILE, data)
                return Zone.from_dict(item)
    return None


def delete_zone(zone_id: int) -> bool:
    with _lock:
        data = _read_json(ZONES_FILE, _EMPTY)
        before = len(data["items"])
        data["items"] = [it for it in data["items"] if it["id"] != zone_id]
        if len(data["items"]) == before:
            return False
        _write_json(ZONES_FILE, data)
    return True


# ==================== Counting (per tanggal, JSONL append-only) ====================

def _date_str(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _append_lines(path: Path, lines: list[str]):
    if not lines:
        return
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def append_count_events(camera_id: int, events: list, when: Optional[datetime.datetime] = None):
    """events: list objek dari `analytics/counting.py` (punya .zone_id, .kelas)."""
    when = when or datetime.datetime.utcnow()
    jam = when.replace(minute=0, second=0, microsecond=0)
    path = COUNTS_DIR / f"{_date_str(when)}.jsonl"
    lines = [
        json.dumps(
            {"camera_id": camera_id, "zone_id": ev.zone_id, "kelas": ev.kelas, "jumlah": 1, "jam": jam.isoformat()},
            ensure_ascii=False,
        )
        for ev in events
    ]
    _append_lines(path, lines)


def _iter_count_rows(since: datetime.datetime, until: Optional[datetime.datetime] = None):
    until = until or datetime.datetime.utcnow()
    day = since.date()
    end_day = until.date()
    one_day = datetime.timedelta(days=1)
    while day <= end_day:
        path = COUNTS_DIR / f"{day.isoformat()}.jsonl"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    jam = datetime.datetime.fromisoformat(row["jam"])
                    if since <= jam <= until:
                        yield row
        day += one_day


def get_summary(camera_id: Optional[int] = None) -> dict:
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    totals = {k: 0 for k in KELAS_LIST}
    for row in _iter_count_rows(today_start):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        if row["kelas"] in totals:
            totals[row["kelas"]] += row["jumlah"]
    totals["total"] = sum(totals[k] for k in KELAS_LIST)
    return totals


def get_volume(camera_id: Optional[int] = None, hours: int = 24) -> list[dict]:
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    buckets: dict[str, dict[str, int]] = {}
    for row in _iter_count_rows(since):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        bucket = buckets.setdefault(row["jam"], {})
        bucket[row["kelas"]] = bucket.get(row["kelas"], 0) + row["jumlah"]

    result = []
    for jam_key in sorted(buckets):
        jam_dt = datetime.datetime.fromisoformat(jam_key)
        entry = {k: buckets[jam_key].get(k, 0) for k in KELAS_LIST}
        entry["jam"] = jam_dt.strftime("%H:%M")
        entry["total"] = sum(entry[k] for k in KELAS_LIST)
        result.append(entry)
    return result


# ==================== Alert (per tanggal, JSONL append-only) ====================

def append_alerts(camera_id: int, alerts: list[dict], when: Optional[datetime.datetime] = None):
    """alerts: list dict {zone_id, tipe, track_id, pesan}."""
    when = when or datetime.datetime.utcnow()
    path = ALERTS_DIR / f"{_date_str(when)}.jsonl"
    ts_ms = int(when.timestamp() * 1000)
    lines = [
        json.dumps(
            {
                "id": f"{ts_ms}-{i}",
                "camera_id": camera_id,
                "zone_id": a.get("zone_id"),
                "tipe": a["tipe"],
                "track_id": a.get("track_id"),
                "pesan": a.get("pesan", ""),
                "created_at": when.isoformat(),
            },
            ensure_ascii=False,
        )
        for i, a in enumerate(alerts)
    ]
    _append_lines(path, lines)


def get_alerts(camera_id: Optional[int] = None, limit: int = 50) -> list[dict]:
    results = []
    for path in sorted(ALERTS_DIR.glob("*.jsonl"), reverse=True):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if camera_id is not None and row["camera_id"] != camera_id:
                continue
            results.append(row)
            if len(results) >= limit:
                return results
    return results
