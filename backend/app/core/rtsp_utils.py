"""Util koneksi RTSP dipakai bersama oleh routes_cameras (test koneksi),
routes_snapshot (ambil 1 frame terbaru untuk background editor poligon), dan
stream_worker (streaming kontinu)."""
import os

import cv2

# Paksa transport TCP + read timeout utk FFmpeg backend-nya OpenCV.
#
# Kenapa ini penting: `cv2.VideoCapture(url).read()` default TIDAK punya
# timeout. Banyak kamera CCTV/NVR lokal default kirim RTSP lewat UDP —
# begitu ada packet loss sedikit di tengah stream, `cap.read()` bisa nge-hang
# selamanya (bukan return False, cuma diam). Test koneksi (baca 1 frame di
# awal, sebelum packet loss kejadian) tetap sukses, tapi worker streaming-nya
# stuck diam2 tanpa error/reconnect — gejalanya UI kejebak di "Menunggu
# stream..." terus meski status kamera sempat "online". TCP transport jauh
# lebih tahan packet loss, dan `stimeout`/timeout prop di bawah memastikan
# `read()` gagal (return False) setelah beberapa detik alih2 hang selamanya,
# supaya logic reconnect yang sudah ada di StreamWorker kepakai.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|stimeout;10000000|max_delay;5000000",
)

OPEN_TIMEOUT_MS = 10000
READ_TIMEOUT_MS = 10000


def open_capture(rtsp_url: str) -> cv2.VideoCapture:
    """Buka `cv2.VideoCapture` utk RTSP dengan transport TCP + timeout,
    dipakai di semua tempat yang connect ke RTSP (worker, test koneksi,
    snapshot) supaya perilakunya konsisten."""
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, OPEN_TIMEOUT_MS)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, READ_TIMEOUT_MS)
    except Exception:
        pass  # properti ini butuh opencv-python cukup baru — aman diabaikan kalau tidak didukung
    return cap


def test_connection(rtsp_url: str, timeout_frames: int = 1) -> tuple[bool, str]:
    """Coba buka stream RTSP dan baca 1 frame. Return (berhasil, pesan)."""
    cap = open_capture(rtsp_url)
    try:
        if not cap.isOpened():
            return False, "Tidak bisa membuka koneksi RTSP"
        ok, frame = cap.read()
        if not ok or frame is None:
            return False, "Koneksi terbuka tapi gagal membaca frame"
        return True, "Koneksi berhasil"
    finally:
        cap.release()


def capture_snapshot(rtsp_url: str):
    """Ambil 1 frame terbaru dari RTSP. Return frame (numpy array BGR) atau
    None kalau gagal."""
    cap = open_capture(rtsp_url)
    try:
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok:
            return None
        return frame
    finally:
        cap.release()
