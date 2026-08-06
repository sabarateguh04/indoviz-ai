import { useEffect, useState } from "react";
import { getModelSettings, setModelSettings } from "../services/api.js";

/** Dropdown model YOLO aktif (global, berlaku untuk semua kamera sekaligus
 * lewat instance detector yang di-share — lihat backend core/detector.py).
 * Ganti pilihan langsung reload model di backend tanpa restart. */
export default function ModelSelector() {
  const [current, setCurrent] = useState("");
  const [available, setAvailable] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getModelSettings()
      .then((data) => {
        setCurrent(data.current);
        setAvailable(data.available);
      })
      .catch(() => {});
  }, []);

  async function handleChange(e) {
    const modelName = e.target.value;
    if (!modelName || modelName === current) return;
    const prev = current;
    setCurrent(modelName);
    setLoading(true);
    setError("");
    try {
      const data = await setModelSettings(modelName);
      setCurrent(data.current);
    } catch (err) {
      setCurrent(prev); // gagal -> balikin ke pilihan sebelumnya
      setError(err.message || "Gagal ganti model");
    } finally {
      setLoading(false);
    }
  }

  if (available.length === 0) return null;

  return (
    <div className="flex items-center gap-1.5" title={error || "Model YOLO aktif — berlaku untuk semua kamera"}>
      <span className="hidden lg:inline text-xs text-brand-100">Model</span>
      <select
        value={current}
        onChange={handleChange}
        disabled={loading}
        className="bg-brand-600 text-white text-xs rounded-md px-2 py-1.5 border border-brand-500 disabled:opacity-60"
      >
        {available.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {loading && <span className="text-xs text-brand-100 animate-pulse">memuat…</span>}
      {error && <span className="text-xs text-red-200">⚠</span>}
    </div>
  );
}
