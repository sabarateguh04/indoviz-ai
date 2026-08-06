import { useEffect, useState } from "react";
import { deleteTrainingFrame, getTrainingFrameImageUrl, getTrainingFrames } from "../services/api.js";

const PAGE_SIZE = 60;
const REFRESH_MS = 15000;

const LABELED_OPTIONS = [
  { value: "", label: "Semua" },
  { value: "false", label: "Belum dilabel" },
  { value: "true", label: "Sudah dilabel" },
];

/** Halaman "Dataset" -- monitoring hasil training/collect_frames.py: apa
 * aja frame yang udah kekumpul per kamera, status labeling-nya, dan bisa
 * hapus frame yang gak representatif sebelum dipakai training. Ini CUMA
 * lihat+kelola hasil yang ada -- proses collect_frames.py sendiri tetap
 * dijalankan manual lewat command line (lihat backend/training/README.md). */
export default function DatasetPage({ cameraNameById = {} }) {
  const [cameraFilter, setCameraFilter] = useState("");
  const [labeledFilter, setLabeledFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [perCamera, setPerCamera] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => setOffset(0), [cameraFilter, labeledFilter]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const data = await getTrainingFrames({
          cameraId: cameraFilter || undefined,
          labeled: labeledFilter === "" ? undefined : labeledFilter === "true",
          limit: PAGE_SIZE,
          offset,
        });
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
          setPerCamera(data.per_camera || {});
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Gagal memuat dataset");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const timer = offset === 0 ? setInterval(load, REFRESH_MS) : null;
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [cameraFilter, labeledFilter, offset, refreshTick]);

  async function handleDelete(filename) {
    if (!window.confirm(`Hapus frame "${filename}"? Tindakan ini tidak bisa dibatalkan.`)) return;
    try {
      await deleteTrainingFrame(filename);
      setRefreshTick((t) => t + 1);
    } catch (err) {
      setError(err.message || "Gagal menghapus frame");
    }
  }

  const totalAll = Object.values(perCamera).reduce((sum, c) => sum + c.total, 0);
  const totalLabeled = Object.values(perCamera).reduce((sum, c) => sum + c.labeled, 0);
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="flex-1 overflow-y-auto p-3">
      <div className="max-w-6xl mx-auto flex flex-col gap-3">
        <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold text-slate-800">Dataset Training</h2>
            <span className="text-sm text-slate-500">
              {totalAll} frame terkumpul · {totalLabeled} sudah dilabel ({totalAll ? Math.round((totalLabeled / totalAll) * 100) : 0}%)
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            Hasil <code className="bg-slate-100 px-1 rounded">training/collect_frames.py</code> -- lihat{" "}
            <code className="bg-slate-100 px-1 rounded">backend/training/README.md</code> buat alur label → build dataset → training.
          </p>

          {Object.keys(perCamera).length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mb-3">
              {Object.entries(perCamera).map(([camId, stat]) => {
                const pct = stat.total ? Math.round((stat.labeled / stat.total) * 100) : 0;
                const name = camId === "unknown" ? "(nama file gak dikenali)" : cameraNameById[camId] || `Kamera #${camId}`;
                return (
                  <div key={camId} className="border border-slate-200 rounded-lg p-2.5">
                    <div className="text-xs font-semibold text-slate-700 truncate">{name}</div>
                    <div className="text-xs text-slate-400 mb-1">
                      {stat.total} frame · {stat.labeled} dilabel
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-400" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            <label className="text-xs font-semibold text-slate-500">Kamera</label>
            <select
              value={cameraFilter}
              onChange={(e) => setCameraFilter(e.target.value)}
              className="border border-slate-300 rounded-lg px-2 py-1 text-sm"
            >
              <option value="">Semua Kamera</option>
              {Object.keys(perCamera)
                .filter((k) => k !== "unknown")
                .map((camId) => (
                  <option key={camId} value={camId}>
                    {cameraNameById[camId] || `Kamera #${camId}`}
                  </option>
                ))}
            </select>

            <label className="text-xs font-semibold text-slate-500 ml-2">Status Label</label>
            <select
              value={labeledFilter}
              onChange={(e) => setLabeledFilter(e.target.value)}
              className="border border-slate-300 rounded-lg px-2 py-1 text-sm"
            >
              {LABELED_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <span className="text-xs text-slate-400 ml-auto">{total} hasil filter</span>
          </div>
        </div>

        {error && <div className="text-sm text-red-600 px-1">{error}</div>}

        {items.length === 0 ? (
          <div className="bg-white rounded-xl shadow border border-slate-200 p-10 text-center text-slate-400 text-sm">
            {loading ? "Memuat…" : "Belum ada frame terkumpul. Jalankan training/collect_frames.py dulu (lihat panduan di atas)."}
          </div>
        ) : (
          <div
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 transition-opacity"
            style={{ opacity: loading ? 0.6 : 1 }}
          >
            {items.map((f) => (
              <div key={f.filename} className="relative group bg-slate-900 rounded-lg overflow-hidden aspect-video">
                <img
                  src={getTrainingFrameImageUrl(f.filename)}
                  alt={f.filename}
                  className="absolute inset-0 w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute top-1 left-1 flex gap-1">
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                      f.labeled ? "bg-emerald-500/90 text-white" : "bg-black/60 text-slate-200"
                    }`}
                  >
                    {f.labeled ? "Dilabel" : "Belum"}
                  </span>
                </div>
                <button
                  onClick={() => handleDelete(f.filename)}
                  title="Hapus frame ini"
                  className="absolute top-1 right-1 w-5 h-5 flex items-center justify-center rounded bg-black/60 text-white text-xs opacity-0 group-hover:opacity-100 hover:bg-red-600 transition"
                >
                  &times;
                </button>
                <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-[10px] px-1.5 py-0.5 truncate">
                  {cameraNameById[f.camera_id] || `#${f.camera_id ?? "?"}`} · {f.jam || ""}
                </div>
              </div>
            ))}
          </div>
        )}

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-500">
              Halaman {page} dari {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                ← Sebelumnya
              </button>
              <button
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                Berikutnya →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
