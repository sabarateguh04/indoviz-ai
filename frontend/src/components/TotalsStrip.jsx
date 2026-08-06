import { useEffect, useState } from "react";
import { getStatsSummary } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 10000;
const EMPTY = Object.fromEntries([...VEHICLE_CLASSES.map((c) => [c.key, 0]), ["total", 0]]);

/** Ringkasan total kendaraan hari ini dgn ikon per kelas + proporsi visual
 * -- dipakai di halaman Utama (yang sengaja dibikin fokus live view aja,
 * bukan analitik detail; itu ada di halaman Analitik lewat StatsSidebar). */
export default function TotalsStrip() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await getStatsSummary();
        if (!cancelled) setSummary(data);
      } catch {
        // biarkan nilai lama tampil kalau request gagal sementara
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const total = summary.total ?? 0;

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-500">Total Hari Ini</h3>
        <div className="text-right leading-tight transition-opacity" style={{ opacity: loading ? 0.6 : 1 }}>
          <span className="text-2xl font-bold text-slate-800 tabular-nums">{total}</span>
          <span className="text-xs text-slate-400 ml-1.5">kendaraan</span>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 transition-opacity" style={{ opacity: loading ? 0.6 : 1 }}>
        {VEHICLE_CLASSES.map((c) => {
          const value = summary[c.key] ?? 0;
          const pct = total ? Math.round((value / total) * 100) : 0;
          return (
            <div key={c.key} className="rounded-lg p-2.5 bg-slate-50 border-t-2" style={{ borderTopColor: c.color }}>
              <div className="flex items-center gap-2">
                <span className="text-xl leading-none shrink-0">{c.icon}</span>
                <div className="min-w-0">
                  <div className="text-lg font-semibold text-slate-800 tabular-nums leading-tight">{value}</div>
                  <div className="text-[11px] text-slate-400 truncate">{c.label}</div>
                </div>
              </div>
              <div className="mt-2 h-1 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: c.color }} />
              </div>
              <div className="text-[10px] text-slate-400 mt-1 text-right tabular-nums">{pct}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
