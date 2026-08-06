"""Endpoint monitoring dataset training (hasil `training/collect_frames.py`)
-- biar user bisa lihat apa aja yang udah kekumpul & status labeling-nya
lewat UI, tanpa buka file explorer manual.

PENTING: endpoint ini CUMA baca+kelola (list/lihat/hapus) file yang sudah
ada di disk. TIDAK menjalankan/menghentikan proses collect_frames.py itu
sendiri -- itu tetap dijalankan manual lewat command line (lihat
training/README.md), karena butuh koneksi RTSP long-running yang gak cocok
dikontrol lewat 1 request HTTP singkat.
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/training", tags=["training"])

TRAINING_DIR = Path(__file__).resolve().parent.parent.parent / "training"
IMAGES_DIR = TRAINING_DIR / "dataset" / "images_raw"
LABELS_DIR = TRAINING_DIR / "dataset" / "labels_raw"

_IMG_EXTS = (".jpg", ".jpeg", ".png")
# Format nama file dari collect_frames.py: {camera_id}_{YYYYMMDD}_{HHMMSS}.jpg
_FILENAME_RE = re.compile(r"^(\d+)_(\d{8})_(\d{6})\.")


def _parse_filename(name: str) -> Optional[dict]:
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    camera_id, date_str, time_str = m.groups()
    return {
        "camera_id": int(camera_id),
        "tanggal": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
        "jam": f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}",
    }


def _safe_image_path(filename: str) -> Path:
    """Cegah path traversal -- filename harus persis nama file yang ada
    langsung di dalam IMAGES_DIR, gak boleh ada '/', '\\', atau '..'."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nama file tidak valid")
    path = IMAGES_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    return path


@router.get("")
def list_frames(
    camera_id: Optional[int] = None,
    labeled: Optional[bool] = None,
    limit: int = 60,
    offset: int = 0,
):
    """List frame hasil collect_frames.py (terbaru dulu) + status label-nya,
    dgn pagination. `per_camera` selalu ringkasan SEMUA frame (gak kefilter)
    biar kelihatan overview total per kamera."""
    if not IMAGES_DIR.exists():
        return {"items": [], "total": 0, "per_camera": {}}

    all_files = sorted(
        (p for p in IMAGES_DIR.iterdir() if p.is_file() and p.suffix.lower() in _IMG_EXTS),
        key=lambda p: p.name,
        reverse=True,
    )

    per_camera: dict[str, dict] = {}
    filtered = []
    for path in all_files:
        meta = _parse_filename(path.name)
        cam_id = meta["camera_id"] if meta else None
        has_label = (LABELS_DIR / f"{path.stem}.txt").exists()

        cam_key = str(cam_id) if cam_id is not None else "unknown"
        stat = per_camera.setdefault(cam_key, {"total": 0, "labeled": 0})
        stat["total"] += 1
        if has_label:
            stat["labeled"] += 1

        if camera_id is not None and cam_id != camera_id:
            continue
        if labeled is not None and has_label != labeled:
            continue
        filtered.append(
            {
                "filename": path.name,
                "camera_id": cam_id,
                "tanggal": meta["tanggal"] if meta else None,
                "jam": meta["jam"] if meta else None,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "labeled": has_label,
            }
        )

    total = len(filtered)
    return {"items": filtered[offset : offset + limit], "total": total, "per_camera": per_camera}


@router.get("/frames/{filename}")
def get_frame_image(filename: str):
    """Serve gambar mentah -- dipakai thumbnail di galeri frontend."""
    path = _safe_image_path(filename)
    return Response(content=path.read_bytes(), media_type="image/jpeg")


@router.delete("/frames/{filename}")
def delete_frame(filename: str):
    """Hapus 1 frame (+ file label-nya kalau ada) -- buat buang frame yang
    gak representatif sebelum dipakai training."""
    path = _safe_image_path(filename)
    path.unlink()
    (LABELS_DIR / f"{path.stem}.txt").unlink(missing_ok=True)
    return {"ok": True}
