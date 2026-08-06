"""Wrapper YOLO (ultralytics) untuk deteksi kendaraan.

Model nano (YOLOv8n / YOLO11n) dipakai supaya bisa jalan multi-stream di
satu GPU. Confidence threshold dipisah per kelas karena motor (objek kecil)
butuh threshold lebih rendah dibanding mobil/bus/truk supaya tidak banyak
miss detection.
"""
import threading

from ultralytics import YOLO

from app.config import settings


class VehicleDetector:
    """Satu instance model YOLO dipakai bersama (shared) oleh semua worker
    stream supaya hemat VRAM. `model.track()` dari ultralytics sendiri
    thread-safe untuk inferensi berurutan, tapi kita tetap pakai lock
    supaya tidak ada race condition saat beberapa worker memanggil model
    yang sama secara bersamaan pada GPU yang sama.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or settings.MODEL_PATH
        self.model = YOLO(self.model_path)
        self.infer_lock = threading.Lock()

    @classmethod
    def get_shared(cls, model_path: str | None = None) -> "VehicleDetector":
        """`model_path` cuma dipakai saat instance pertama kali dibuat
        (biasanya dipanggil sekali di startup dengan model pilihan user yang
        tersimpan). Panggilan berikutnya tanpa argumen akan mengembalikan
        instance yang sama."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(model_path)
        return cls._instance

    def reload(self, model_path: str):
        """Ganti model aktif tanpa restart backend. Karena semua kamera pakai
        instance shared yang sama, ganti di sini otomatis berlaku ke semua
        stream pada frame berikutnya."""
        with self.infer_lock:
            self.model = YOLO(model_path)
            self.model_path = model_path

    def track(self, frame, imgsz: int | None = None, persist: bool = True):
        """Jalankan deteksi + tracking (ByteTrack bawaan ultralytics) pada
        satu frame. Confidence filter per-kelas diterapkan di
        `tracker.py` setelah hasil mentah didapat, karena `model.track()`
        hanya menerima satu nilai `conf` global.
        """
        classes = list(settings.VEHICLE_CLASS_MAP.keys())
        conf_min = min(settings.CONF_THRESHOLD_DEFAULT, settings.CONF_THRESHOLD_MOTOR)

        with self.infer_lock:
            results = self.model.track(
                frame,
                imgsz=imgsz or settings.IMGSZ_DEFAULT,
                conf=conf_min,
                classes=classes,
                persist=persist,
                tracker="bytetrack.yaml",
                verbose=False,
            )
        return results[0]
