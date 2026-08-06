"""Rakit dataset YOLO dari gambar (images_raw/) + label (labels_raw/) hasil
proses manual (lihat training/README.md), jadi struktur siap-training:

    training/dataset/
      images/train/*.jpg   images/val/*.jpg
      labels/train/*.txt   labels/val/*.txt
      data.yaml

Urutan kelas SENGAJA dibuat konsisten dengan `VEHICLE_CLASS_MAP` di
`app/config.py` (motor, mobil, bus, truk) supaya gampang di-swap nanti --
lihat catatan di training/README.md soal update config.py setelah training.

Pemakaian (dari folder backend/, venv aktif):

    python -m training.build_dataset
    python -m training.build_dataset --val-ratio 0.15 --seed 42
    python -m training.build_dataset --include-unlabeled-as-background
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRAINING_DIR = Path(__file__).resolve().parent
RAW_IMAGES_DIR = TRAINING_DIR / "dataset" / "images_raw"
RAW_LABELS_DIR = TRAINING_DIR / "dataset" / "labels_raw"
OUT_DIR = TRAINING_DIR / "dataset"

# Urutan ini = urutan class_id (0,1,2,3) di file label .txt hasil labeling.
# HARUS sama dengan urutan yang dipakai saat setup project di tool labeling
# (lihat training/README.md).
CLASS_NAMES = ["motor", "mobil", "bus", "truk"]

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def _find_images(images_dir: Path) -> list[Path]:
    return sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMG_EXTS)


def build(images_dir: Path, labels_dir: Path, out_dir: Path, val_ratio: float, seed: int,
          include_unlabeled_as_background: bool):
    if not images_dir.exists():
        print(f"Folder gambar tidak ada: {images_dir}")
        return

    images = _find_images(images_dir)
    if not images:
        print(f"Tidak ada gambar di {images_dir}. Jalankan training/collect_frames.py dulu.")
        return

    pairs: list[tuple[Path, Path]] = []
    skipped_unlabeled = 0
    for img in images:
        label = labels_dir / f"{img.stem}.txt"
        if label.exists():
            pairs.append((img, label))
        elif include_unlabeled_as_background:
            # Gambar tanpa objek sama sekali (background/hard-negative) --
            # label kosong itu valid di format YOLO (artinya: 0 objek).
            pairs.append((img, None))
        else:
            skipped_unlabeled += 1

    if skipped_unlabeled:
        print(f"Skip {skipped_unlabeled} gambar yang belum ada label-nya "
              f"(taruh .txt di {labels_dir}, atau pakai --include-unlabeled-as-background "
              f"kalau itu memang gambar kosong/tanpa kendaraan).")

    if not pairs:
        print("Tidak ada pasangan gambar+label yang siap dipakai. Selesaikan labeling dulu.")
        return

    random.seed(seed)
    random.shuffle(pairs)
    n_val = max(1, int(len(pairs) * val_ratio)) if len(pairs) > 4 else 0
    val_pairs = pairs[:n_val]
    train_pairs = pairs[n_val:]

    for split, split_pairs in (("train", train_pairs), ("val", val_pairs)):
        img_out = out_dir / "images" / split
        lbl_out = out_dir / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)
        for img, label in split_pairs:
            shutil.copy2(img, img_out / img.name)
            if label is not None:
                shutil.copy2(label, lbl_out / f"{img.stem}.txt")
            else:
                (lbl_out / f"{img.stem}.txt").write_text("", encoding="utf-8")

    data_yaml = out_dir / "data.yaml"
    data_yaml.write_text(
        "path: " + str(out_dir.resolve()).replace("\\", "/") + "\n"
        "train: images/train\n"
        "val: images/val\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names: {CLASS_NAMES}\n",
        encoding="utf-8",
    )

    print(f"Dataset siap: {len(train_pairs)} train, {len(val_pairs)} val")
    print(f"data.yaml: {data_yaml}")
    print("Lanjut: python -m training.train")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images-dir", type=Path, default=RAW_IMAGES_DIR)
    parser.add_argument("--labels-dir", type=Path, default=RAW_LABELS_DIR)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-unlabeled-as-background", action="store_true",
                         help="Gambar tanpa file .txt label dianggap 'tidak ada objek' (hard negative), "
                              "bukan di-skip. Berguna khusus utk frame gelap/silau tanpa kendaraan.")
    args = parser.parse_args()
    build(args.images_dir, args.labels_dir, args.out, args.val_ratio, args.seed,
          args.include_unlabeled_as_background)


if __name__ == "__main__":
    main()
