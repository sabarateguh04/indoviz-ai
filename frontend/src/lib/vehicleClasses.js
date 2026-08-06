/** Definisi kelas kendaraan terpusat (nama, label ID, warna) — dipakai
 * bareng oleh StatsSidebar, VolumeChart, dan CameraCard supaya warnanya
 * konsisten di seluruh app (bukan didefinisikan ulang di tiap komponen).
 *
 * Urutan & warna divalidasi colorblind-safe (protan/deutan/tritan) pakai
 * dataviz skill's validate_palette.js -- ALL CHECKS PASS di light mode.
 * "tidak_diketahui" sengaja dikasih abu-abu netral (bukan dari palet
 * kategorikal) karena secara semantik itu bukan kelas "asli", melainkan
 * bucket fallback (lihat core/tracker.py backend).
 */
export const VEHICLE_CLASSES = [
  { key: "motor", label: "Motor", color: "#2a78d6" },
  { key: "mobil", label: "Mobil", color: "#eb6834" },
  { key: "bus", label: "Bus", color: "#1baf7a" },
  { key: "truk", label: "Truk", color: "#eda100" },
  { key: "tidak_diketahui", label: "Tidak Diketahui", color: "#94a3b8" },
];

export const VEHICLE_CLASS_COLORS = Object.fromEntries(VEHICLE_CLASSES.map((c) => [c.key, c.color]));
export const VEHICLE_CLASS_LABELS = Object.fromEntries(VEHICLE_CLASSES.map((c) => [c.key, c.label]));
