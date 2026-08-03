# Frontend — Analitik Kamera (IndoVIS)

Dashboard React + Vite untuk analitik CCTV: manajemen kamera & zona, live
multi-kamera, grafik volume per jam, dan panel alert (wrong-way/parkir
liar/pelanggaran jalur).

## Instalasi

```bash
cd frontend
npm install
```

## Menjalankan (dev)

```bash
npm run dev
```

Frontend jalan di `http://localhost:5173`. Request `/api/*` dan koneksi
`/ws/live` di-proxy ke backend (`http://localhost:8000`) lewat konfigurasi
di `vite.config.js` — pastikan backend sudah jalan lebih dulu.

## Build produksi

```bash
npm run build
npm run preview
```

## Alur pemakaian

1. Klik **Kelola Kamera** di top bar untuk menambah kamera baru (nama +
   RTSP URL). Tombol **Test Koneksi** mengecek RTSP-nya lebih dulu lewat
   backend sebelum disimpan.
2. Setelah kamera tersimpan, klik **Atur Zona** untuk membuka editor
   poligon: klik titik demi titik di atas snapshot kamera, pilih tipe zona
   (counting / larangan parkir / arah / jalur), lalu simpan.
3. Dashboard utama menampilkan live feed multi-kamera (layout 2x2 / 1+3 /
   wide / single, bisa diganti dari top bar) lengkap dengan overlay bbox,
   badge REC/fps, dan status koneksi kamera.
4. Sidebar kanan menampilkan total kendaraan hari ini, grafik volume per
   jam, dan panel alert real-time.
