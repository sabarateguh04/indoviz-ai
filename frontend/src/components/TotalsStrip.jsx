import { useEffect, useState } from "react";
import { getStatsSummary } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 10000;
const EMPTY = Object.fromEntries([...VEHICLE_CLASSES.map((c) => [c.key, 0]), ["total", 0]]);

/** Strip ringkas total kendaraan hari ini dgn ikon -- dipakai di halaman
 * Utama (yang sengaja dibikin fokus live view aja, bukan analitik detail;
 * itu ada di halaman Analitik lewat StatsSidebar). */
export default function TotalsStrip() {
  const [summary, setSummary] = useState(EMPTY);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getStatsSummary();
        if (!cancelled) setSummary(data);
      } catch {
        // biarkan nilai lama tampil kalau request gagal sementara
      }
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 px-4 py-2.5 flex items-center gap-5 overflow-x-auto">
      <span className="text-xs font-semibold text-slate-400 shrink-0">Total Hari Ini</span>
      {VEHICLE_CLASSES.map((c) => (
        <div key={c.key} className="flex items-center gap-1.5 shrink-0">
          <span className="text-lg leading-none">{c.icon}</span>
          <span className="text-base font-semibold text-slate-800 tabular-nums">{summary[c.key] ?? 0}</span>
          <span className="text-xs text-slate-400">{c.label}</span>
        </div>
      ))}
      <div className="ml-auto flex items-center gap-1.5 shrink-0 pl-4 border-l border-slate-200">
        <span className="text-xs text-slate-400">Total</span>
        <span className="text-base font-bold text-slate-800 tabular-nums">{summary.total ?? 0}</span>
      </div>
    </div>
  );
}
