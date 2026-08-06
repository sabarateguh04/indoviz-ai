import { useEffect, useState } from "react";
import { deleteStatsEvents, getStatsEvents } from "../services/api.js";
import { VEHICLE_CLASSES, VEHICLE_CLASS_COLORS, VEHICLE_CLASS_LABELS } from "../lib/vehicleClasses.js";

const PAGE_SIZE = 25;
const REFRESH_MS = 10000;

const ZONE_TIPE_LABEL = {
  counting: "Counting",
  no_parking: "Larangan Parkir",
  direction: "Arah",
  lane: "Jalur",
};

function formatWaktu(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("id-ID", { hour12: false });
}

/** Tabel mentah tiap event deteksi/counting (1 baris = 1 kendaraan lolos
 * zona) -- beda dari StatsSidebar/VolumeChart yang sudah teragregasi.
 * Ikut filter kamera/tanggal/tipe-zona global (App.jsx), + filter kelas
 * lokal khusus tabel ini. Juga punya tombol hapus data sesuai filter aktif. */
export default function DetectionEventsModal({ cameraId, date, zoneType, cameraNameById = {}, onClose }) {
  const [kelasFilter, setKelasFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => setOffset(0), [cameraId, date, zoneType, kelasFilter]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const data = await getStatsEvents(cameraId, {
          date,
          zoneType,
          kelas: kelasFilter || undefined,
          limit: PAGE_SIZE,
          offset,
        });
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Gagal memuat data deteksi");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    // Auto-refresh cuma di halaman pertama -- di halaman lain, event baru
    // bakal geser offset dan bikin bingung kalau dipaksa refresh.
    const timer = offset === 0 ? setInterval(load, REFRESH_MS) : null;
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [cameraId, date, zoneType, kelasFilter, offset, refreshTick]);

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const filterDesc = [
    date ? `tanggal ${date}` : "hari ini",
    cameraId ? `kamera "${cameraNameById[cameraId] || `#${cameraId}`}"` : "semua kamera",
    zoneType ? `tipe zona "${ZONE_TIPE_LABEL[zoneType] || zoneType}"` : "semua tipe zona",
    kelasFilter ? `kelas "${VEHICLE_CLASS_LABELS[kelasFilter]}"` : "semua kelas",
  ].join(", ");

  async function handleDelete() {
    if (total === 0) return;
    const ok = window.confirm(
      `Hapus ${total} event deteksi (${filterDesc})?\n\nTindakan ini TIDAK BISA DIBATALKAN.`
    );
    if (!ok) return;
    setDeleting(true);
    setError("");
    try {
      await deleteStatsEvents(cameraId, { date, zoneType, kelas: kelasFilter || undefined });
      setOffset(0);
      setRefreshTick((t) => t + 1);
    } catch (err) {
      setError(err.message || "Gagal menghapus data");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 shrink-0">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Data Deteksi</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Histori mentah tiap kendaraan yang lolos hitung zona{date ? ` — ${date}` : " — hari ini"}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2 shrink-0 flex-wrap">
          <label className="text-xs font-semibold text-slate-500">Kelas</label>
          <select
            value={kelasFilter}
            onChange={(e) => setKelasFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-2 py-1 text-sm"
          >
            <option value="">Semua Kelas</option>
            {VEHICLE_CLASSES.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-400">{total} event</span>

          <button
            onClick={handleDelete}
            disabled={deleting || total === 0}
            title={`Hapus semua data sesuai filter saat ini: ${filterDesc}`}
            className="ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold text-red-600 border border-red-200 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {deleting ? "Menghapus…" : "🗑 Hapus data sesuai filter"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto transition-opacity" style={{ opacity: loading ? 0.6 : 1 }}>
          {error && <div className="text-sm text-red-600 px-5 py-3">{error}</div>}
          {!error && items.length === 0 && (
            <div className="text-sm text-slate-400 text-center py-10">Belum ada data deteksi</div>
          )}
          {items.length > 0 && (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500 text-left">
                <tr>
                  <th className="px-5 py-2 font-semibold">Waktu</th>
                  <th className="px-3 py-2 font-semibold">Kamera</th>
                  <th className="px-3 py-2 font-semibold">Zona</th>
                  <th className="px-3 py-2 font-semibold">Kelas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((ev, i) => (
                  <tr key={`${ev.waktu}-${i}`} className="hover:bg-slate-50">
                    <td className="px-5 py-2 text-slate-600 tabular-nums whitespace-nowrap">{formatWaktu(ev.waktu)}</td>
                    <td className="px-3 py-2 text-slate-700 truncate max-w-[10rem]">
                      {cameraNameById[ev.camera_id] || ev.camera_nama}
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {ev.zone_nama || ZONE_TIPE_LABEL[ev.zone_tipe] || "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: VEHICLE_CLASS_COLORS[ev.kelas] || "#94a3b8" }}
                        />
                        {VEHICLE_CLASS_LABELS[ev.kelas] || ev.kelas}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="px-5 py-3 border-t border-slate-200 flex items-center justify-between text-sm shrink-0">
          <span className="text-slate-500">
            Halaman {page} dari {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              ← Sebelumnya
            </button>
            <button
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              Berikutnya →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
