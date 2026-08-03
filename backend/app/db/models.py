import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    rtsp_url = Column(String, nullable=False)
    status = Column(String, default="offline")  # online | warning | offline
    active = Column(Boolean, default=True)  # apakah worker harus berjalan utk kamera ini

    # Konfigurasi deteksi per-kamera (opsional, override default global)
    imgsz = Column(Integer, nullable=True)

    # Kalibrasi kecepatan: {"pixel_points": [[x1,y1],[x2,y2]], "distance_m": 10.0}
    speed_calibration = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    counts = relationship("CountHistory", back_populates="camera", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="camera", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    nama = Column(String, default="")
    # tipe_zona: counting | no_parking | direction | lane
    tipe_zona = Column(String, nullable=False)

    # Koordinat poligon, list [[x,y], ...] relatif ke resolusi frame asli (piksel)
    koordinat = Column(JSON, nullable=False)

    # Untuk zona tipe "direction": arah normal dalam derajat (0-360, 0 = arah +x)
    arah_normal_deg = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    camera = relationship("Camera", back_populates="zones")


class CountHistory(Base):
    __tablename__ = "count_history"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    kelas = Column(String, nullable=False)  # motor | mobil | bus | truk
    jumlah = Column(Integer, default=1)
    jam = Column(DateTime, nullable=False)  # dibulatkan ke awal jam, utk agregat per jam

    camera = relationship("Camera", back_populates="counts")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    # tipe: wrong_way | illegal_parking | lane_violation
    tipe = Column(String, nullable=False)
    track_id = Column(Integer, nullable=True)
    pesan = Column(String, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    camera = relationship("Camera", back_populates="alerts")
