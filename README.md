# Analitik Kamera - IndoVIS
Sistem analitik CCTV counting kendaraan + fitur lanjutan.
Struktur: analitik_kamera/backend (Python) dan analitik_kamera/frontend (Node.js)

## Branch `main` vs `main-prod`

- **`main`** — baseline, jalan di PC biasa (CPU, tanpa GPU/CUDA).
- **`main-prod`** — turunan `main`, dioptimalkan untuk mesin dengan GPU
  NVIDIA (dites di RTX 3060 Ti): fix stabilitas koneksi RTSP (transport
  TCP + timeout, sebelumnya bisa hang diam-diam saat streaming), deteksi
  GPU/CPU otomatis, enhancement footage malam (CLAHE), dan kategori
  kendaraan "tidak diketahui" untuk deteksi confidence rendah alih-alih
  dibuang. Kodenya tetap fallback ke CPU otomatis kalau tidak ada GPU —
  lihat `backend/README.md` bagian "Update di branch main-prod" untuk
  detail lengkap & cara pasang torch versi CUDA.
