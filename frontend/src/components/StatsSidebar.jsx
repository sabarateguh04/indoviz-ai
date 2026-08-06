import { useEffect, useState } from "react";
import { getStatsSummary } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 10000;
const EMPTY_SUMMARY = Object.fromEntries([...VEHICLE_CLASSES.map((c) => [c.key, 0]), ["total", 0]]);

export default function StatsSidebar({ cameraId, date, zoneType }) {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const data = await getStatsSummary(cameraId, { date, zoneType });
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
  }, [cameraId, date, zoneType]);

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-500">{date ? `Total Tanggal ${date}` : "Total Hari Ini"}</h3>
        {loading && <span className="text-xs text-slate-400 animate-pulse">memuat…</span>}
      </div>
      <div className="grid grid-cols-2 gap-3 transition-opacity" style={{ opacity: loading ? 0.7 : 1 }}>
        {VEHICLE_CLASSES.map((c) => {
          const unknown = c.key === "tidak_diketahui";
          return (
            <div
              key={c.key}
              className={`rounded-lg p-3 text-center border-t-2 ${unknown ? "col-span-2 bg-slate-50" : "bg-slate-50"}`}
              style={{ borderTopColor: c.color }}
            >
              <div className="text-2xl font-semibold text-slate-800 tabular-nums">{summary[c.key] ?? 0}</div>
              <div className="text-xs text-slate-500 mt-0.5">{c.label}</div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-sm">
        <span className="text-slate-500">Total kendaraan</span>
        <span className="font-bold text-slate-800 tabular-nums">{summary.total ?? 0}</span>
      </div>
    </div>
  );
}
