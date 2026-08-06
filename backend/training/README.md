# Fine-tuning YOLO khusus kamera IndoVIS

Model bawaan (`yolo11n/s/m.pt`) dilatih di COCO — foto siang/warna biasa.
Di footage CCTV kondisi ekstrem (silau lampu malam bikin badan kendaraan
jadi siluet hitam total, ditambah distorsi lensa fisheye), model generik
bisa gagal total mendeteksi walau objeknya jelas kelihatan buat mata
manusia. Bukan soal threshold/GPU/kode — model belum pernah "lihat" bentuk
kayak gitu. Satu-satunya fix yang benar-benar ampuh untuk kasus ini:
**fine-tuning** model pakai footage dari kamera kamu sendiri.

Kabar baiknya: fine-tuning (lanjut dari checkpoint COCO, bukan training
dari nol) jauh lebih murah dari yang dibayangkan — ratusan gambar
berlabel (bukan puluhan ribu) sudah bisa kelihatan perbaikannya, dan
prosesnya di RTX 3060 Ti cuma hitungan jam, bukan hari.

## Alur kerja

```
1. collect_frames.py   -> ambil frame mentah dari kamera (siang+malam)
2. label manual         -> gambar kotak di sekeliling tiap kendaraan
3. build_dataset.py     -> rakit jadi struktur YOLO (train/val split)
4. train.py             -> fine-tuning dari yolo11s.pt
5. deploy               -> taruh best.pt di models_weights/, update config.py
```

### 1. Kumpulin frame

```bash
cd backend
.venv\Scripts\activate
python -m training.collect_frames --camera-id 2 --minutes 120
```

Jalankan di jam & kondisi yang bermasalah (malam, hujan, jam sibuk) DAN di
kondisi normal (siang cerah) — model perlu contoh dari kedua kondisi biar
tidak lupa cara deteksi di siang hari. Script otomatis nyimpen 2 jenis
frame: sampling periodik (`--interval`, default tiap 30 detik) + trigger
saat ada gerakan (motion-diff antar frame) supaya momen ada kendaraan lewat
tidak kelewat cuma karena pas di antara 2 sampling periodik.

Target awal yang masuk akal: **300–500 gambar berlabel**, makin banyak
makin baik terutama utk kondisi silau/malam yang jadi masalah utama.
Gambar mentah masuk ke `training/dataset/images_raw/`.

### 2. Label manual

Ini bagian yang butuh mata manusia — gambar kotak (bounding box) di
sekeliling tiap kendaraan yang kelihatan, termasuk yang cuma keliatan
sebagai **siluet gelap** karena silau (justru itu intinya: ngajarin model
"bentuk siluet begini = truk/motor", bukan cuma dari foto yang jelas).

Rekomendasi tool (gratis, langsung export format YOLO):

- **[makesense.ai](https://www.makesense.ai/)** — jalan di browser, tidak
  perlu install apa-apa. Upload gambar dari `images_raw/`, bikin label
  list persis urutan ini (harus sama, urutannya menentukan class_id):
  ```
  motor
  mobil
  bus
  truk
  ```
  Gambar kotak per kendaraan, lalu export "YOLO format" — taruh semua
  `.txt` hasilnya di `training/dataset/labels_raw/` (nama file harus sama
  persis dengan nama gambar, cuma beda ekstensi: `2_20260807_220301.jpg`
  -> `2_20260807_220301.txt`).
- **[LabelImg](https://github.com/HumanSignal/labelImg)** — alternatif
  aplikasi desktop (`pip install labelImg`), kalau mau kerja offline.

Kalau ada gambar yang memang kosong (tidak ada kendaraan sama sekali) —
tidak perlu dikasih file `.txt`, biarkan saja; opsional dimasukkan sebagai
*hard negative* lewat flag di langkah 3 (`--include-unlabeled-as-background`)
supaya model juga belajar "kondisi begini = memang tidak ada apa-apa",
mengurangi false positive.

### 3. Rakit dataset

```bash
python -m training.build_dataset
# atau, kalau mau ikutkan gambar kosong sbg hard-negative:
python -m training.build_dataset --include-unlabeled-as-background
```

Otomatis split train/val (85/15 default) + bikin `dataset/data.yaml`.

### 4. Fine-tuning

```bash
python -m training.train --base yolo11s.pt --epochs 100 --imgsz 960
```

Pantau di `training/runs/indoviz/` (grafik loss/precision/recall, contoh
prediksi di val set). Kalau training keputus di tengah jalan:
`python -m training.train --resume`.

### 5. Deploy model hasil fine-tuning

1. Copy `training/runs/indoviz/weights/best.pt` ke
   `app/models_weights/` (mis. rename jadi `indoviz_v1.pt`).
2. **PENTING** — update `VEHICLE_CLASS_MAP` & `MOTOR_CLASS_ID` di
   `app/config.py`. Model hasil fine-tuning ini class_id-nya urutan
   sendiri (0=motor, 1=mobil, 2=bus, 3=truk — sesuai `CLASS_NAMES` di
   `build_dataset.py`), BEDA dari model COCO asli (2=mobil, 3=motor,
   5=bus, 7=truk). Kalau lupa update ini, deteksi bakal salah label
   total (mobil kebaca motor, dst).
   ```python
   VEHICLE_CLASS_MAP = {0: "motor", 1: "mobil", 2: "bus", 3: "truk"}
   MOTOR_CLASS_ID = 0
   ```
3. Tambahkan nama file model itu ke `AVAILABLE_MODELS` di `config.py`
   (opsional, cuma buat referensi — dropdown model di UI otomatis baca
   file `.pt` yang ada di `models_weights/`, tidak wajib terdaftar di sini).
4. Restart backend, pilih model itu lewat dropdown "Model" di UI (atau
   `PUT /api/settings/model`).

## Alternatif/pelengkap: perbaikan di sisi kamera

Fine-tuning butuh waktu (kumpulin data + label + iterasi). Sambil jalan,
cek juga setting kamera/NVR — sering kali ini lebih cepat & lebih murah:

- **WDR (Wide Dynamic Range)** — kalau kamera/NVR support, aktifkan.
  Ini didesain persis untuk kondisi highlight meledak (lampu silau) +
  shadow gelap dalam 1 frame yang sama.
- **Kurangi intensitas IR** kalau kameranya IR (infrared) malam — IR yang
  terlalu terang mantul dari jalan basah/aspal bikin overexposure lokal.
- **Backlight compensation / exposure manual** — kalau ada opsi shutter
  speed manual, coba naikkan sedikit (lebih cepat) khusus buat area yang
  sering kena silau, supaya highlight tidak "meledak" total jadi putih.

Ini biasanya diatur lewat web admin NVR/kamera langsung (bukan lewat
aplikasi IndoVIS ini) — merek NVR yang dipakai (URL RTSP-nya pola
`.../cam/realmonitor?channel=N&subtype=0`) kompatibel dengan software
config macam Dahua SmartPSS / DMSS App.

## Struktur folder (setelah dipakai)

```
training/
  collect_frames.py
  build_dataset.py
  train.py
  dataset/              # di-gitignore, isinya data lokal
    images_raw/
    labels_raw/
    images/train, images/val
    labels/train, labels/val
    data.yaml
  runs/                  # di-gitignore, hasil training (checkpoint, log)
```
