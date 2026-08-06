# Backend — Analitik Kamera (IndoVIS)

> Branch **`main-prod`**: varian production dari `main`, dioptimalkan untuk
> mesin dengan GPU NVIDIA (dites di RTX 3060 Ti). Berisi fix stabilitas
> koneksi RTSP, deteksi otomatis GPU/CPU, enhancement footage malam, dan
> kategori "tidak diketahui" — lihat bagian **Update di branch main-prod**
> di bawah. Kodenya tetap jalan di PC tanpa GPU (fallback CPU otomatis);
> branch `main` sengaja dipertahankan apa adanya sebagai baseline paling
> ringan/generik.

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
- Deteksi yang confidence-nya di bawah threshold per-kelas tapi masih di
  atas `CONF_THRESHOLD_UNKNOWN` (default 0.15) TETAP dihitung — dilabel
  kelas `tidak_diketahui` alih-alih dibuang. Lihat detail di bagian
  **Update di branch main-prod**.
- `imgsz` per kamera bisa dinaikkan (960/1280) lewat field `imgsz` saat
  update kamera, khusus kamera dengan banyak motor kecil. Dites di GPU
  RTX 3060 Ti: yolo11s @ imgsz 960 ≈ 16ms/frame (~60 FPS kapasitas per
  stream), jadi headroom-nya cukup besar untuk beberapa kamera sekaligus.
- Fine-tuning di footage CCTV asli (siang+malam, termasuk kondisi silau)
  adalah langkah paling ampuh & terukur kalau model COCO generik masih
  gagal deteksi di kondisi ekstrem (mis. siluet gelap karena silau lampu).
  Pipeline lengkapnya (kumpulin frame -> label -> build dataset -> training)
  ada di `training/` — lihat `training/README.md`.
- Semua fitur analitik lanjutan (speed, wrong-way, dsb) mewarisi akurasi
  model deteksi dasar — bukan model terpisah.

## Update di branch main-prod

Perbaikan & fitur berikut ditambahkan di branch ini (tidak ada di `main`):

- **Fix: koneksi RTSP putus diam-diam saat streaming (`core/rtsp_utils.py`,
  `core/stream_worker.py`).** Sebelumnya `cv2.VideoCapture(url).read()`
  dipanggil tanpa timeout — begitu ada packet loss di tengah stream (umum
  di RTSP lewat UDP), `read()` bisa hang selamanya tanpa error, sehingga
  logic reconnect yang ada tidak pernah kepicu. Gejalanya: status kamera
  sempat "online" tapi live view macet permanen di "Menunggu stream...".
  Fix: helper `open_capture()` baru memaksa `rtsp_transport=tcp` (lebih
  tahan packet loss) + read/open timeout 10 detik lewat FFmpeg capture
  options, dipakai konsisten di worker streaming, test koneksi, dan
  snapshot zona.
- **Robustness: worker tidak lagi mati diam-diam.** Proses per-frame
  (inferensi + semua modul `analytics/`) di `StreamWorker.run()` dibungkus
  `try/except` + log — error tak terduga di satu frame tidak lagi
  mematikan seluruh thread worker kamera tsb tanpa jejak.
- **GPU otomatis (`core/detector.py`).** Model YOLO otomatis pindah ke GPU
  (CUDA) + FP16 kalau `torch.cuda.is_available()`, fallback CPU kalau
  tidak ada. Override manual lewat `YOLO_DEVICE` di `.env` (`auto` / `cpu`
  / `cuda:0` dst). **Butuh build torch yang CUDA-enabled** — `pip install`
  biasa sering narik build CPU-only; install dari index resmi PyTorch
  sesuai versi CUDA driver-mu, contoh (cek versi yang cocok di
  https://pytorch.org/get-started/locally/):
  ```bash
  pip uninstall torch torchvision -y
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
  ```
  Verifikasi: `python -c "import torch; print(torch.cuda.is_available())"`
  harus `True`. Log startup backend juga mencetak `device=cuda:0 half=True`
  kalau berhasil kepakai (lihat `VehicleDetector.__init__`).
- **Enhancement footage malam/low-light (`core/detector.py`,
  `_enhance_low_light`).** Kalau kecerahan rata-rata frame di bawah
  `LOW_LIGHT_BRIGHTNESS_THRESHOLD` (default 80/255), frame di-CLAHE
  (contrast-limited adaptive histogram equalization) dulu sebelum masuk
  model — menaikkan kontras lokal supaya bentuk kendaraan lebih kebentuk
  di footage CCTV IR malam yang gelap/low-contrast. Bisa dimatikan lewat
  `ENABLE_LOW_LIGHT_ENHANCE=false`.
- **Kategori "tidak_diketahui" (`core/tracker.py`, `db/store.py`).**
  Sebelumnya, deteksi dengan confidence di bawah threshold per-kelas
  langsung dibuang. Sekarang model dijalankan dengan floor confidence
  lebih rendah (`CONF_THRESHOLD_UNKNOWN`, default 0.15); yang lolos floor
  ini tapi tidak lolos threshold per-kelas tetap dihitung & masuk zona
  (counting/dll), cuma dilabel `tidak_diketahui` — dipakai di frontend
  (stat tile, grafik volume, overlay bbox berwarna abu-abu) sebagai
  "ada kendaraan lewat, tipe belum jelas" alih-alih hilang tanpa jejak.

## Scope

Fitur ANPR, deteksi helm, deteksi lampu merah, deteksi kecelakaan, dan
multi-camera re-id SENGAJA belum diimplementasikan — di luar kapasitas
perangkat saat ini (target 8-15 stream RTSP bersamaan di RTX 3060 Ti 8GB).
