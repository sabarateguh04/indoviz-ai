import { useEffect, useState } from "react";
import { getDisplaySettings, setDisplaySettings } from "../services/api.js";

/** Dropdown kecepatan tampilan live view (global, berlaku ke semua kamera).
 * Ini KOSMETIK doang -- ngatur seberapa sering frame JPEG dikirim ke
 * browser lewat WebSocket. Deteksi & counting TIDAK ikut lambat/cepat
 * karena ini, itu selalu jalan di frame rate penuh di backend (lihat
 * core/stream_worker.py). Naikin fps di sini cuma bikin video di browser
 * lebih smooth, dengan trade-off bandwidth/CPU broadcast per kamera. */

const PRESETS = [
  { fps: 5, interval: 0.2, label: "5 fps (hemat bandwidth)" },
  { fps: 10, interval: 0.1, label: "10 fps (smooth)" },
  { fps: 15, interval: 0.0667, label: "15 fps (lebih smooth)" },
  { fps: 20, interval: 0.05, label: "20 fps (maksimal)" },
];

function closestPreset(interval) {
  return PRESETS.reduce((best, p) => (Math.abs(p.interval - interval) < Math.abs(best.interval - interval) ? p : best));
}

export default function DisplaySettings() {
  const [interval, setInterval_] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getDisplaySettings()
      .then((data) => setInterval_(data.ws_broadcast_interval))
      .catch(() => {});
  }, []);

  async function handleChange(e) {
    const value = parseFloat(e.target.value);
    const prev = interval;
    setInterval_(value);
    setLoading(true);
    setError("");
    try {
      await setDisplaySettings(value);
    } catch (err) {
      setInterval_(prev);
      setError(err.message || "Gagal ganti kecepatan live view");
    } finally {
      setLoading(false);
    }
  }

  if (interval === null) return null;

  const current = closestPreset(interval);

  return (
    <div
      className="flex items-center gap-1.5"
      title={error || "Kecepatan tampilan live view -- kosmetik saja, tidak mempengaruhi kecepatan counting/deteksi"}
    >
      <span className="hidden lg:inline text-xs text-brand-100">Live</span>
      <select
        value={current.interval}
        onChange={handleChange}
        disabled={loading}
        className="bg-brand-600 text-white text-xs rounded-md px-2 py-1.5 border border-brand-500 disabled:opacity-60"
      >
        {PRESETS.map((p) => (
          <option key={p.fps} value={p.interval}>
            {p.label}
          </option>
        ))}
      </select>
      {loading && <span className="text-xs text-brand-100 animate-pulse">memuat…</span>}
      {error && <span className="text-xs text-red-200">⚠</span>}
    </div>
  );
}
