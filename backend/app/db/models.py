"""Model data kamera & zona — sekarang disimpan sebagai file JSON (lihat
`app/db/store.py`), bukan tabel database SQL. Dataclass di sini cuma
representasi in-memory supaya kode lain (routes, stream_worker) bisa akses
lewat atribut (`camera.rtsp_url`) seperti sebelumnya."""
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Camera:
    id: int
    nama: str
    rtsp_url: str
    status: str = "offline"  # online | warning | offline
    active: bool = True  # apakah worker harus berjalan utk kamera ini
    imgsz: Optional[int] = None  # override ukuran input inferensi per-kamera
    # Kalibrasi kecepatan: {"pixel_points": [[x1,y1],[x2,y2]], "distance_m": 10.0}
    speed_calibration: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Camera":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class Zone:
    id: int
    camera_id: int
    nama: str = ""
    tipe_zona: str = "counting"  # counting | no_parking | direction | lane
    # Poligon [[x,y], ...] relatif ke resolusi frame asli (piksel)
    koordinat: list = field(default_factory=list)
    # Untuk tipe 'direction': arah normal dalam derajat (0-360, 0 = arah +x)
    arah_normal_deg: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Zone":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})
