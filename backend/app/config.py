"""Konfigurasi aplikasi — dibaca dari environment variable / file .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Penyimpanan data: file JSON (bukan SQL), dipisah per kategori & tanggal
    # supaya tiap file tetap kecil — lihat app/db/store.py.
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "app" / "data")))

    # Model YOLO
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR / "app" / "models_weights" / "yolo11n.pt"))

    # Confidence threshold per kelas — motor pakai threshold lebih rendah
    # karena objek kecil dan sering tidak terdeteksi di model nano.
    CONF_THRESHOLD_DEFAULT: float = float(os.getenv("CONF_THRESHOLD_DEFAULT", "0.4"))
    CONF_THRESHOLD_MOTOR: float = float(os.getenv("CONF_THRESHOLD_MOTOR", "0.25"))

    # Ukuran input inferensi default. Bisa dinaikkan per-kamera (lihat
    # kolom Camera.imgsz) untuk kamera dengan banyak motor/objek kecil.
    IMGSZ_DEFAULT: int = int(os.getenv("IMGSZ_DEFAULT", "640"))

    # Kelas kendaraan yang dipakai (indeks kelas COCO bawaan YOLO).
    # 2=car, 3=motorcycle, 5=bus, 7=truck
    VEHICLE_CLASS_MAP = {2: "mobil", 3: "motor", 5: "bus", 7: "truk"}
    MOTOR_CLASS_ID = 3

    # Direktori snapshot sementara (dipakai background editor poligon)
    SNAPSHOT_DIR: Path = BASE_DIR / "app" / "snapshots"

    # Interval broadcast websocket (detik) supaya tidak membanjiri client
    WS_BROADCAST_INTERVAL: float = float(os.getenv("WS_BROADCAST_INTERVAL", "0.2"))

    # Parkir liar: threshold gerak (piksel, dinormalisasi ke diagonal frame)
    # dan durasi diam minimal (detik) sebelum dianggap parkir liar.
    ILLEGAL_PARKING_MOVE_THRESHOLD: float = float(os.getenv("ILLEGAL_PARKING_MOVE_THRESHOLD", "0.01"))
    ILLEGAL_PARKING_SECONDS: float = float(os.getenv("ILLEGAL_PARKING_SECONDS", "10"))

    # Kepadatan: threshold jumlah objek per zona per interval untuk klasifikasi
    CONGESTION_INTERVAL_SECONDS: float = float(os.getenv("CONGESTION_INTERVAL_SECONDS", "10"))
    CONGESTION_PADAT_THRESHOLD: int = int(os.getenv("CONGESTION_PADAT_THRESHOLD", "8"))
    CONGESTION_MACET_THRESHOLD: int = int(os.getenv("CONGESTION_MACET_THRESHOLD", "15"))

    # Wrong-way: sudut minimal (derajat) antara arah gerak objek vs arah
    # normal zona supaya dianggap melawan arah.
    WRONG_WAY_ANGLE_THRESHOLD: float = float(os.getenv("WRONG_WAY_ANGLE_THRESHOLD", "120"))


settings = Settings()
settings.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
Path(settings.MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
