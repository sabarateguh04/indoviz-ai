"""State per-kamera yang dipertahankan lintas frame oleh `stream_worker.py`.

Semua modul di `analytics/` menerima objek `CameraState` yang sama supaya
mereka bisa membaca histori posisi/track tanpa masing-masing menyimpan
state sendiri-sendiri (tracker & deteksi yang dipakai tetap satu, sesuai
instruksi build: jangan bikin model AI terpisah per fitur).
"""
import time
from collections import defaultdict, deque

HISTORY_LEN = 30
STALE_AFTER_SECONDS = 30


class CameraState:
    def __init__(self):
        # track_id -> deque[(timestamp, (x, y))], posisi centroid terbaru
        self.track_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
        self.track_class: dict[int, str] = {}

        # counting.py — zone_id -> set(track_id) yang sudah terhitung
        self.counted_in_zone: dict[int, set] = defaultdict(set)

        # illegal_parking.py
        self.stationary_since: dict[int, float] = {}
        self.stationary_anchor: dict[int, tuple] = {}
        self.illegal_parking_alerted: set = set()

        # wrong_way.py — hindari alert berulang tiap frame utk track sama
        self.wrong_way_alerted: set = set()

        # lane_violation.py — track_id -> zone_id jalur asal saat pertama masuk
        self.track_home_lane: dict[int, int] = {}
        self.lane_violation_alerted: set = set()

        # congestion.py — zone_id -> deque[(timestamp, jumlah_objek)]
        self.zone_count_samples: dict[int, deque] = defaultdict(lambda: deque(maxlen=500))

        self._last_seen: dict[int, float] = {}

    def update_track_position(self, track_id: int, class_name: str, centroid: tuple, timestamp: float):
        self.track_history[track_id].append((timestamp, centroid))
        self.track_class[track_id] = class_name
        self._last_seen[track_id] = timestamp

    def cleanup_stale(self, now: float | None = None):
        """Buang state track yang sudah tidak terlihat > STALE_AFTER_SECONDS
        supaya memory tidak terus bertambah untuk kendaraan yang sudah lewat."""
        now = now or time.time()
        stale_ids = [tid for tid, ts in self._last_seen.items() if now - ts > STALE_AFTER_SECONDS]
        for tid in stale_ids:
            self.track_history.pop(tid, None)
            self.track_class.pop(tid, None)
            self.stationary_since.pop(tid, None)
            self.stationary_anchor.pop(tid, None)
            self.illegal_parking_alerted.discard(tid)
            self.wrong_way_alerted.discard(tid)
            self.track_home_lane.pop(tid, None)
            self.lane_violation_alerted.discard(tid)
            self._last_seen.pop(tid, None)
