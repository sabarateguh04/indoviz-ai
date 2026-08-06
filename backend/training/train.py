"""Fine-tune YOLO dari dataset hasil `training/build_dataset.py`.

Fine-tuning (lanjut dari checkpoint COCO pre-trained, BUKAN training dari
nol) butuh jauh lebih sedikit data & waktu dibanding training from-scratch
-- beberapa ratus gambar berlabel yang representatif (siang+malam, kondisi
silau/hujan/dsb yang mau ditangani) sudah cukup buat mulai lihat perbaikan.

Pemakaian (dari folder backend/, venv aktif, butuh GPU CUDA):

    python -m training.train
    python -m training.train --base yolo11s.pt --epochs 100 --imgsz 960
    python -m training.train --resume   # lanjutin run yang keputus

Hasil: training/runs/indoviz/weights/best.pt -- lihat training/README.md
utk langkah setelah ini (update config.py, taruh di models_weights/).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRAINING_DIR = Path(__file__).resolve().parent
DATA_YAML = TRAINING_DIR / "dataset" / "data.yaml"
RUNS_DIR = TRAINING_DIR / "runs"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DATA_YAML)
    parser.add_argument("--base", default="yolo11s.pt",
                         help="Model awal buat fine-tuning (checkpoint COCO pre-trained), default yolo11s.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0", help="'0' = GPU pertama, 'cpu' = paksa CPU")
    parser.add_argument("--patience", type=int, default=20, help="Early-stop kalau val gak membaik N epoch")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"data.yaml belum ada: {args.data}\nJalankan training/build_dataset.py dulu.")
        return

    from ultralytics import YOLO

    model = YOLO(args.base)
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=str(RUNS_DIR),
        name="indoviz",
        resume=args.resume,
    )
    print("\nSelesai. Bandingkan metrik di training/runs/indoviz/, lalu:")
    print("  1. Copy training/runs/indoviz/weights/best.pt ke app/models_weights/ "
          "(mis. jadi indoviz_v1.pt)")
    print("  2. Update VEHICLE_CLASS_MAP & MOTOR_CLASS_ID di app/config.py sesuai urutan "
          "kelas baru (lihat training/README.md)")
    print("  3. Pilih model itu lewat dropdown 'Model' di UI (atau PUT /api/settings/model)")


if __name__ == "__main__":
    main()
