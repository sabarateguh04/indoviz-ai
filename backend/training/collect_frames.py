"""Kumpulin frame dari kamera RTSP yang sudah terdaftar (app/data/cameras.json)
buat bahan dataset fine-tuning YOLO.

Kenapa perlu ini: model COCO generik (yolo11n/s/m) sering gagal deteksi
kendaraan di footage CCTV kondisi ekstrem -- silau lampu malam bikin badan
kendaraan jadi siluet hitam total, ditambah distorsi lensa fisheye. Ini
bukan soal threshold, tapi model belum pernah "lihat" bentuk seperti itu.
Fine-tuning di footage kamera sendiri adalah jalan paling akurat, tapi butuh
dataset gambar dari kamera itu sendiri, mencakup siang, malam, hujan, dan
kondisi lain yang bakal dihadapi.

Strategi sampling:
- Interval biasa (`--interval`, default 30 detik) -- coverage kondisi umum.
- Trigger gerakan (motion-diff antar frame) -- coverage momen ada kendaraan
  lewat, dibatasi `--motion-cooldown` detik supaya tidak spam duplikat
  hampir identik dari 1 kendaraan yang sama.

Pemakaian (dari folder backend/, venv aktif):

    python -m training.collect_frames --camera-id 2 --minutes 120
    python -m training.collect_frames --semua --minutes 120

Frame disimpan ke `training/dataset/images_raw/{camera_id}_{timestamp}.jpg`.
Langkah berikutnya: label manual (lihat training/README.md), lalu jalankan
`training/build_dataset.py`.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.rtsp_utils import open_capture  # noqa: E402
from app.db import store  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "dataset" / "images_raw"


def _motion_score(prev_gray, gray) -> float:
    diff = cv2.absdiff(prev_gray, gray)
    return float(diff.mean())


def collect(camera_id: int, rtsp_url: str, minutes: float, interval: float, motion_threshold: float,
            motion_cooldown: float, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = open_capture(rtsp_url)
    if not cap.isOpened():
        print(f"[camera_id={camera_id}] gagal buka RTSP, skip")
        return

    end_at = time.time() + minutes * 60
    last_periodic_save = 0.0
    last_motion_save = 0.0
    prev_gray = None
    saved = 0

    print(f"[camera_id={camera_id}] mulai koleksi {minutes} menit "
          f"(interval={interval}s, motion_threshold={motion_threshold})")

    try:
        while time.time() < end_at:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(1.0)
                cap.release()
                cap = open_capture(rtsp_url)
                continue

            now = time.time()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_small = cv2.resize(gray, (160, 90))

            should_save = False
            reason = ""
            if now - last_periodic_save >= interval:
                should_save = True
                reason = "periodic"
            elif prev_gray is not None and now - last_motion_save >= motion_cooldown:
                score = _motion_score(prev_gray, gray_small)
                if score >= motion_threshold:
                    should_save = True
                    reason = f"motion(score={score:.1f})"

            if should_save:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = out_dir / f"{camera_id}_{ts}.jpg"
                cv2.imwrite(str(path), frame)
                saved += 1
                print(f"  saved {path.name} ({reason})")
                last_periodic_save = now
                last_motion_save = now

            prev_gray = gray_small
            time.sleep(1.0)  # cukup 1 fps buat sampling, gak perlu full frame rate
    finally:
        cap.release()
        print(f"[camera_id={camera_id}] selesai, {saved} frame tersimpan di {out_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera-id", type=int, help="ID kamera tunggal (lihat GET /api/cameras)")
    parser.add_argument("--semua", action="store_true", help="Koleksi dari semua kamera aktif sekaligus")
    parser.add_argument("--minutes", type=float, default=60, help="Lama koleksi per kamera (menit), default 60")
    parser.add_argument("--interval", type=float, default=30, help="Interval sampling periodik (detik), default 30")
    parser.add_argument("--motion-threshold", type=float, default=8.0,
                         help="Skor motion-diff (0-255) minimal buat trigger simpan ekstra, default 8.0 -- "
                              "turunkan kalau kendaraan jarang ke-trigger, naikkan kalau kebanyakan noise")
    parser.add_argument("--motion-cooldown", type=float, default=3.0,
                         help="Jeda minimal antar simpan akibat motion (detik), default 3.0")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Folder output")
    args = parser.parse_args()

    if not args.camera_id and not args.semua:
        parser.error("isi --camera-id <id> atau --semua")

    cameras = store.list_active_cameras() if args.semua else [store.get_camera(args.camera_id)]
    cameras = [c for c in cameras if c is not None]
    if not cameras:
        print("Tidak ada kamera aktif ditemukan.")
        return

    for cam in cameras:
        collect(cam.id, cam.rtsp_url, args.minutes, args.interval, args.motion_threshold,
                args.motion_cooldown, args.out)


if __name__ == "__main__":
    main()
