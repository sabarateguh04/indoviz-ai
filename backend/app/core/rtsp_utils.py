"""Util koneksi RTSP dipakai bersama oleh routes_cameras (test koneksi) dan
routes_snapshot (ambil 1 frame terbaru untuk background editor poligon)."""
import cv2


def test_connection(rtsp_url: str, timeout_frames: int = 1) -> tuple[bool, str]:
    """Coba buka stream RTSP dan baca 1 frame. Return (berhasil, pesan)."""
    cap = cv2.VideoCapture(rtsp_url)
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
    cap = cv2.VideoCapture(rtsp_url)
    try:
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok:
            return None
        return frame
    finally:
        cap.release()
