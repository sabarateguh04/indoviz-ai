# Backend — Analitik Kamera (IndoVIS)

Backend FastAPI untuk analitik CCTV: counting kendaraan per jenis, estimasi
kecepatan, deteksi lawan arah, deteksi parkir liar, kepadatan per zona, dan
deteksi pelanggaran jalur. Deteksi & tracking pakai YOLO nano (ultralytics)
+ ByteTrack.

## Instalasi

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
copy .env.example .env    # Windows, atau: cp .env.example .env
```

Taruh file model YOLO nano (mis. `yolo11n.pt`, otomatis ter-download
ultralytics saat pertama kali dipakai kalau belum ada) di
`app/models_weights/`. Path-nya diatur lewat `MODEL_PATH` di `.env`.

## Menjalankan

```bash
uvicorn app.main:app --reload
```

Backend jalan di `http://localhost:8000`. Dokumentasi API otomatis di
`http://localhost:8000/docs`.

## Alur kerja

1. Tambah kamera lewat endpoint `/api/cameras` (atau lewat UI frontend) —
   isi nama + RTSP URL. Semua kamera dikelola lewat penyimpanan JSON, TIDAK
   hardcode di `.env`.
2. Setelah kamera tersimpan, ambil snapshot lewat `/api/snapshot/{id}` untuk
   dipakai sebagai background gambar poligon zona.
3. Simpan poligon zona lewat `/api/zones` (tipe: `counting`, `no_parking`,
   `direction`, `lane`).
4. Begitu kamera & zona tersimpan (dan kamera berstatus aktif), worker
   stream (`app/core/stream_worker.py`) otomatis mulai memproses RTSP-nya
   di background thread — tidak perlu restart backend.
5. Data live (bbox, counting, alert, kepadatan) di-broadcast lewat
   WebSocket `/ws/live`. Statistik agregat tersedia lewat `/api/stats/*`.

## Penyimpanan data

Tidak pakai SQLite/PostgreSQL — semua data disimpan sebagai file JSON di
`app/data/` (path diatur lewat `DATA_DIR` di `.env`), dipisah per kategori
dan per tanggal supaya tiap file tetap kecil:

```
app/data/
  cameras.json             # daftar kamera (kategori, jarang berubah)
  zones.json               # daftar zona (kategori, jarang berubah)
  counts/2026-08-03.jsonl  # event counting kendaraan, 1 file per hari
  alerts/2026-08-03.jsonl  # event alert (wrong-way/parkir liar/dsb), 1 file per hari
```

`counts/` dan `alerts/` pakai format JSONL (1 baris = 1 event, append-only)
supaya tidak perlu baca+tulis ulang seluruh histori tiap ada event baru.
Folder `app/data/` di-gitignore karena isinya data runtime, bukan kode.

## Uji coba tanpa kamera CCTV asli

Untuk tes pipeline dulu tanpa RTSP asli, isi `rtsp_url` kamera dengan path
file video lokal (OpenCV `VideoCapture` menerima path file biasa juga),
misalnya `C:/video/contoh.mp4`.

## Catatan akurasi

- Confidence threshold kelas motor dibuat lebih rendah (`CONF_THRESHOLD_MOTOR`,
  default 0.25) dibanding kelas lain (`CONF_THRESHOLD_DEFAULT`, default 0.4)
  karena motor sering tidak terdeteksi model nano akibat ukuran objek kecil.
- `imgsz` per kamera bisa dinaikkan (960/1280) lewat field `imgsz` saat
  update kamera, khusus kamera dengan banyak motor kecil.
- Folder `training/` disiapkan sebagai tempat dataset lokal untuk
  fine-tuning model nanti (belum ada isinya di tahap ini).
- Semua fitur analitik lanjutan (speed, wrong-way, dsb) mewarisi akurasi
  model deteksi dasar — bukan model terpisah.

## Scope

Fitur ANPR, deteksi helm, deteksi lampu merah, deteksi kecelakaan, dan
multi-camera re-id SENGAJA belum diimplementasikan — di luar kapasitas
perangkat saat ini (target 8-15 stream RTSP bersamaan di RTX 3060 Ti 8GB).
