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

CATATAN WAKTU: semua timestamp di modul ini SENGAJA pakai jam LOKAL server
(`datetime.datetime.now()`), BUKAN UTC (`utcnow()`). App ini single-locale
(dipakai di WIB, UTC+7) dan "hari ini"/"jam sekian" itu maknanya jam
dinding operator, bukan UTC. Sebelumnya sempat pakai `utcnow()` dan itu
BUG -- filter tanggal "hari ini" bisa nampilin 0 (event dari jam 00:00-
07:00 WIB kehitung "kemarin" secara UTC), dan kolom jam di grafik volume
kegeser 7 jam dari jam dinding asli. Kalau nanti mau dukung multi-timezone,
ganti ke datetime timezone-aware (`datetime.now(ZoneInfo(...))`) di sini,
bukan balik ke naive UTC.
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
SETTINGS_FILE = DATA_DIR / "settings.json"
COUNTS_DIR = DATA_DIR / "counts"
ALERTS_DIR = DATA_DIR / "alerts"

KELAS_LIST = ["motor", "mobil", "bus", "truk", "tidak_diketahui"]

_EMPTY = {"next_id": 1, "items": []}
_DEFAULT_SETTINGS = {"model_name": None, "ws_broadcast_interval": None}


def init_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COUNTS_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    if not CAMERAS_FILE.exists():
        _write_json(CAMERAS_FILE, dict(_EMPTY))
    if not ZONES_FILE.exists():
        _write_json(ZONES_FILE, dict(_EMPTY))
    if not SETTINGS_FILE.exists():
        _write_json(SETTINGS_FILE, dict(_DEFAULT_SETTINGS))


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
            view_enabled=payload.get("view_enabled", True),
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


# ==================== Pengaturan aplikasi (mis. model YOLO aktif) ====================

def get_app_settings() -> dict:
    with _lock:
        data = _read_json(SETTINGS_FILE, _DEFAULT_SETTINGS)
    return {**_DEFAULT_SETTINGS, **data}


def update_app_settings(changes: dict) -> dict:
    with _lock:
        data = _read_json(SETTINGS_FILE, _DEFAULT_SETTINGS)
        data.update(changes)
        _write_json(SETTINGS_FILE, data)
        return {**_DEFAULT_SETTINGS, **data}


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


def _zone_type_map() -> dict[int, str]:
    """zone_id -> tipe_zona, dipakai untuk filter stats/alerts per tipe zona
    (event counting/alert cuma nyimpen zone_id, bukan tipe_zona-nya)."""
    return {z.id: z.tipe_zona for z in list_zones()}


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
    when = when or datetime.datetime.now()
    jam = when.replace(minute=0, second=0, microsecond=0)
    path = COUNTS_DIR / f"{_date_str(when)}.jsonl"
    lines = [
        json.dumps(
            {
                "camera_id": camera_id,
                "zone_id": ev.zone_id,
                "kelas": ev.kelas,
                "jumlah": 1,
                "jam": jam.isoformat(),
                # Timestamp presisi (bukan cuma dibulatkan ke jam) -- dipakai
                # tabel "Data Deteksi" di frontend. `jam` (dibulatkan) tetap
                # dipertahankan apa adanya krn dipakai bucketing get_volume().
                "waktu": when.isoformat(),
            },
            ensure_ascii=False,
        )
        for ev in events
    ]
    _append_lines(path, lines)


def _day_range(date_str: str) -> tuple[datetime.datetime, datetime.datetime]:
    """Parse 'YYYY-MM-DD' jadi rentang [00:00:00, 23:59:59.999999] hari itu."""
    day_start = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    day_end = day_start + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
    return day_start, day_end


def _iter_count_rows(since: datetime.datetime, until: Optional[datetime.datetime] = None):
    until = until or datetime.datetime.now()
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
                    # Pakai `waktu` (presisi detik) kalau ada, fallback ke
                    # `jam` (dibulatkan) utk event lama sblm field ini ada.
                    # Penting utk granularitas menit di get_timeseries --
                    # filter by `jam` bisa salah buang event yg persis
                    # kejadian di awal rentang tapi jam-nya dibulatkan ke
                    # sebelum `since`.
                    ts = datetime.datetime.fromisoformat(row.get("waktu") or row["jam"])
                    if since <= ts <= until:
                        yield row
        day += one_day


def get_summary(camera_id: Optional[int] = None, date: Optional[str] = None, zone_type: Optional[str] = None) -> dict:
    if date:
        since, until = _day_range(date)
    else:
        since = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        until = None

    zone_map = _zone_type_map() if zone_type else None
    totals = {k: 0 for k in KELAS_LIST}
    for row in _iter_count_rows(since, until):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        if zone_map is not None and zone_map.get(row.get("zone_id")) != zone_type:
            continue
        if row["kelas"] in totals:
            totals[row["kelas"]] += row["jumlah"]
    totals["total"] = sum(totals[k] for k in KELAS_LIST)
    return totals


def get_volume(
    camera_id: Optional[int] = None,
    hours: int = 24,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
) -> list[dict]:
    if date:
        since, until = _day_range(date)
    else:
        since = datetime.datetime.now() - datetime.timedelta(hours=hours)
        until = None

    zone_map = _zone_type_map() if zone_type else None
    buckets: dict[str, dict[str, int]] = {}
    for row in _iter_count_rows(since, until):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        if zone_map is not None and zone_map.get(row.get("zone_id")) != zone_type:
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


def get_count_events(
    camera_id: Optional[int] = None,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
    kelas: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List mentah tiap event counting (1 baris = 1 kendaraan lolos zona) --
    dipakai tabel "Data Deteksi" di frontend, beda dari get_summary/get_volume
    yang sudah teragregasi. Terbaru dulu."""
    if date:
        since, until = _day_range(date)
    else:
        since = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        until = None

    zone_type_map = _zone_type_map()  # zone_id -> tipe_zona, selalu dibangun (dipakai buat tampilan JUGA, bukan cuma filter)
    zone_names = {z.id: z.nama for z in list_zones()}
    camera_names = {c.id: c.nama for c in list_cameras()}

    rows = []
    for row in _iter_count_rows(since, until):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        if zone_type is not None and zone_type_map.get(row.get("zone_id")) != zone_type:
            continue
        if kelas is not None and row["kelas"] != kelas:
            continue
        rows.append(
            {
                # Event lama (sblm field `waktu` ditambahkan) fallback ke `jam`
                # (presisi jam bulat) supaya tetap tampil, bukan error.
                "waktu": row.get("waktu") or row["jam"],
                "camera_id": row["camera_id"],
                "camera_nama": camera_names.get(row["camera_id"], f"Kamera #{row['camera_id']}"),
                "zone_id": row.get("zone_id"),
                "zone_nama": zone_names.get(row.get("zone_id")) or "",
                "zone_tipe": zone_type_map.get(row.get("zone_id")),
                "kelas": row["kelas"],
            }
        )

    rows.sort(key=lambda r: r["waktu"], reverse=True)
    total = len(rows)
    return {"items": rows[offset : offset + limit], "total": total}


# ==================== Alert (per tanggal, JSONL append-only) ====================

def append_alerts(camera_id: int, alerts: list[dict], when: Optional[datetime.datetime] = None):
    """alerts: list dict {zone_id, tipe, track_id, pesan}."""
    when = when or datetime.datetime.now()
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


def get_alerts(
    camera_id: Optional[int] = None,
    limit: int = 50,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
) -> list[dict]:
    zone_map = _zone_type_map() if zone_type else None
    if date:
        # Tanggal spesifik -> baca cuma 1 file, urutan tetap terbaru dulu.
        paths = [ALERTS_DIR / f"{date}.jsonl"]
    else:
        paths = sorted(ALERTS_DIR.glob("*.jsonl"), reverse=True)

    results = []
    for path in paths:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if camera_id is not None and row["camera_id"] != camera_id:
                continue
            if zone_map is not None and zone_map.get(row.get("zone_id")) != zone_type:
                continue
            results.append(row)
            if len(results) >= limit:
                return results
    return results


# ==================== Time-series fleksibel (grafik line, halaman Analitik) ====================

_BULAN_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

_GRANULARITY_STEP = {
    "minute": datetime.timedelta(minutes=1),
    "hour": datetime.timedelta(hours=1),
    "day": datetime.timedelta(days=1),
    "week": datetime.timedelta(weeks=1),
    # "month" ditangani khusus di _add_months krn panjang bulan gak tetap
}
GRANULARITY_DEFAULT_COUNT = {"minute": 60, "hour": 24, "day": 30, "week": 12, "month": 12}


def _truncate_to_granularity(dt: datetime.datetime, granularity: str) -> datetime.datetime:
    if granularity == "minute":
        return dt.replace(second=0, microsecond=0)
    if granularity == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if granularity == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "week":
        d = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return d - datetime.timedelta(days=d.weekday())  # Senin sbg awal minggu
    if granularity == "month":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"granularity tidak dikenal: {granularity!r} (harus salah satu dari {list(GRANULARITY_DEFAULT_COUNT)})")


def _add_months(dt: datetime.datetime, n: int) -> datetime.datetime:
    month0 = dt.month - 1 + n
    year = dt.year + month0 // 12
    month = month0 % 12 + 1
    return dt.replace(year=year, month=month)


def _step_bucket(dt: datetime.datetime, granularity: str) -> datetime.datetime:
    return _add_months(dt, 1) if granularity == "month" else dt + _GRANULARITY_STEP[granularity]


def _format_bucket_label(dt: datetime.datetime, granularity: str) -> str:
    if granularity in ("minute", "hour"):
        return dt.strftime("%H:%M")
    if granularity in ("day", "week"):
        return dt.strftime("%d/%m")
    if granularity == "month":
        return f"{_BULAN_ID[dt.month - 1]} {dt.year}"
    return dt.isoformat()


def get_timeseries(
    camera_id: Optional[int] = None,
    zone_type: Optional[str] = None,
    granularity: str = "hour",
    count: Optional[int] = None,
) -> list[dict]:
    """Time-series count kendaraan per bucket (menit/jam/hari/minggu/bulan),
    N bucket terakhir dari sekarang mundur -- dipakai grafik line + tabel di
    halaman Analitik. Beda dari get_volume (cuma per-jam dlm 1 hari): ini
    fleksibel granularitasnya dan selalu window "N terakhir dari sekarang",
    bukan terikat 1 tanggal spesifik."""
    if granularity not in GRANULARITY_DEFAULT_COUNT:
        raise ValueError(f"granularity harus salah satu dari {list(GRANULARITY_DEFAULT_COUNT)}")
    count = count or GRANULARITY_DEFAULT_COUNT[granularity]
    count = max(1, min(count, 366))  # batas wajar biar gak query kebablasan

    now = datetime.datetime.now()
    until_bucket = _truncate_to_granularity(now, granularity)
    since_bucket = until_bucket
    for _ in range(count - 1):
        since_bucket = (
            _add_months(since_bucket, -1) if granularity == "month" else since_bucket - _GRANULARITY_STEP[granularity]
        )

    zone_map = _zone_type_map() if zone_type else None
    buckets: dict[str, dict[str, int]] = {}
    for row in _iter_count_rows(since_bucket, now):
        if camera_id is not None and row["camera_id"] != camera_id:
            continue
        if zone_map is not None and zone_map.get(row.get("zone_id")) != zone_type:
            continue
        ts = datetime.datetime.fromisoformat(row.get("waktu") or row["jam"])
        key = _truncate_to_granularity(ts, granularity).isoformat()
        bucket = buckets.setdefault(key, {})
        bucket[row["kelas"]] = bucket.get(row["kelas"], 0) + row["jumlah"]

    # Generate SEMUA bucket dlm rentang (termasuk yg kosong/0) biar sumbu
    # waktu di grafik line kontinu, bukan cuma bucket yg ada datanya.
    result = []
    cursor = since_bucket
    for _ in range(count):
        key = cursor.isoformat()
        entry = {k: buckets.get(key, {}).get(k, 0) for k in KELAS_LIST}
        entry["waktu"] = key
        entry["label"] = _format_bucket_label(cursor, granularity)
        entry["total"] = sum(entry[k] for k in KELAS_LIST)
        result.append(entry)
        cursor = _step_bucket(cursor, granularity)
    return result


# ==================== Hapus data (admin -- tabel Data Deteksi) ====================

def _write_jsonl_or_remove(path: Path, kept_lines: list[str]):
    """Tulis ulang file JSONL dgn baris yang tersisa (atomik), atau hapus
    filenya sekalian kalau isinya jadi kosong."""
    with _lock:
        if not kept_lines:
            path.unlink(missing_ok=True)
            return
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(kept_lines) + "\n")
        tmp.replace(path)


def delete_count_events(
    camera_id: Optional[int] = None,
    date: Optional[str] = None,
    zone_type: Optional[str] = None,
    kelas: Optional[str] = None,
) -> int:
    """Hapus event counting yang cocok filter (dipakai tombol hapus di tabel
    "Data Deteksi"). WAJIB minimal 1 filter diisi -- ini operasi destruktif,
    jangan sampai bisa kehapus SEMUA data cuma krn lupa isi filter. Return
    jumlah baris yang dihapus.

    CATATAN penting: `date` kosong DI SINI artinya "hari ini" (konsisten
    dgn get_count_events/get_summary), BUKAN "sepanjang masa" -- default
    operasi destruktif harus yang paling sempit/aman, supaya tidak ada
    kejutan "klik hapus di tabel yg nampilin data hari ini, eh yang
    kehapus malah data dari tanggal2 lain juga"."""
    if camera_id is None and date is None and zone_type is None and kelas is None:
        raise ValueError("Isi minimal 1 filter (tanggal/kamera/kategori) sebelum menghapus data")

    target_date = date or _date_str(datetime.datetime.now())
    zone_type_map = _zone_type_map() if zone_type else None
    paths = [COUNTS_DIR / f"{target_date}.jsonl"]

    total_deleted = 0
    for path in paths:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        kept = []
        deleted_here = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            matches = (
                (camera_id is None or row["camera_id"] == camera_id)
                and (zone_type is None or zone_type_map.get(row.get("zone_id")) == zone_type)
                and (kelas is None or row["kelas"] == kelas)
            )
            if matches:
                deleted_here += 1
            else:
                kept.append(stripped)

        if deleted_here:
            _write_jsonl_or_remove(path, kept)
            total_deleted += deleted_here

    return total_deleted
