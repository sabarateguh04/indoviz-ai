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

function todayStr() {
  return new Date().toLocaleDateString("sv-SE"); // format YYYY-MM-DD, aman dari timezone shift
}

/** Panel hapus data -- filter kamera/kategori/rentang tanggal SENDIRI,
 * independen dari filter tabel di atasnya (defaultnya ngikutin filter
 * tabel biar praktis, tapi bisa diubah bebas -- mis. mau hapus rentang
 * beberapa hari sekaligus walau tabelnya lagi nampilin 1 hari doang). */
function DeletePanel({ cameras, initialCameraId, initialKelas, initialDate, cameraNameById, onDeleted }) {
  const [camId, setCamId] = useState(initialCameraId ?? "");
  const [kelas, setKelas] = useState(initialKelas ?? "");
  const [dateFrom, setDateFrom] = useState(initialDate || todayStr());
  const [dateTo, setDateTo] = useState(initialDate || todayStr());
  const [previewTotal, setPreviewTotal] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function preview() {
      setPreviewTotal(null);
      try {
        const data = await getStatsEvents(camId || undefined, {
          dateFrom,
          dateTo,
          kelas: kelas || undefined,
          limit: 1,
        });
        if (!cancelled) setPreviewTotal(data.total);
      } catch {
        if (!cancelled) setPreviewTotal(null);
      }
    }
    preview();
    return () => {
      cancelled = true;
    };
  }, [camId, kelas, dateFrom, dateTo]);

  const rangeDesc = dateFrom === dateTo ? `tanggal ${dateFrom}` : `${dateFrom} s/d ${dateTo}`;
  const filterDesc = [
    rangeDesc,
    camId ? `kamera "${cameraNameById[camId] || `#${camId}`}"` : "semua kamera",
    kelas ? `kelas "${VEHICLE_CLASS_LABELS[kelas]}"` : "semua kelas",
  ].join(", ");

  async function handleDelete() {
    if (!previewTotal) return;
    const ok = window.confirm(`Hapus ${previewTotal} event deteksi (${filterDesc})?\n\nTindakan ini TIDAK BISA DIBATALKAN.`);
    if (!ok) return;
    setDeleting(true);
    setError("");
    try {
      await deleteStatsEvents(camId || undefined, {
        date: dateFrom === dateTo ? dateFrom : undefined,
        dateFrom: dateFrom !== dateTo ? dateFrom : undefined,
        dateTo: dateFrom !== dateTo ? dateTo : undefined,
        kelas: kelas || undefined,
      });
      onDeleted();
    } catch (err) {
      setError(err.message || "Gagal menghapus data");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="px-5 py-3 border-b border-slate-100 bg-red-50/50 space-y-2.5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Dari tanggal</label>
          <input
            type="date"
            value={dateFrom}
            max={dateTo}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Sampai tanggal</label>
          <input
            type="date"
            value={dateTo}
            min={dateFrom}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Kamera</label>
          <select value={camId} onChange={(e) => setCamId(e.target.value)} className="w-full border border-slate-300 rounded-lg px-2 py-1 text-sm">
            <option value="">Semua Kamera</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nama}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-0.5">Kategori</label>
          <select value={kelas} onChange={(e) => setKelas(e.target.value)} className="w-full border border-slate-300 rounded-lg px-2 py-1 text-sm">
            <option value="">Semua Kelas</option>
            {VEHICLE_CLASSES.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="text-xs text-red-600">{error}</div>}

      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-slate-500">
          {previewTotal === null ? "Menghitung…" : `${previewTotal} event akan dihapus (${filterDesc})`}
        </span>
        <button
          onClick={handleDelete}
          disabled={deleting || !previewTotal}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {deleting ? "Menghapus…" : "🗑 Hapus Sekarang"}
        </button>
      </div>
    </div>
  );
}

/** Tabel mentah tiap event deteksi/counting (1 baris = 1 kendaraan lolos
 * zona) -- beda dari StatsSidebar/VolumeChart yang sudah teragregasi.
 * Ikut filter kamera/tanggal/tipe-zona global (App.jsx), + filter kelas
 * lokal khusus tabel ini. Juga punya panel hapus data (filter sendiri:
 * kamera/kategori/rentang tanggal). */
export default function DetectionEventsModal({ cameras = [], cameraId, date, zoneType, cameraNameById = {}, onClose }) {
  const [kelasFilter, setKelasFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);
  const [deletePanelOpen, setDeletePanelOpen] = useState(false);

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
            onClick={() => setDeletePanelOpen((v) => !v)}
            className="ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold text-red-600 border border-red-200 hover:bg-red-50"
          >
            {deletePanelOpen ? "Tutup panel hapus" : "🗑 Hapus data…"}
          </button>
        </div>

        {deletePanelOpen && (
          <DeletePanel
            cameras={cameras}
            initialCameraId={cameraId}
            initialKelas={kelasFilter}
            initialDate={date}
            cameraNameById={cameraNameById}
            onDeleted={() => {
              setOffset(0);
              setRefreshTick((t) => t + 1);
            }}
          />
        )}

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
