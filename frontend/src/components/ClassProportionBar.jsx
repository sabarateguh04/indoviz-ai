import { useEffect, useState } from "react";
import { getStatsSummary } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 15000;

/** Part-to-whole: proporsi kelas kendaraan hari ini, 1 bar horizontal
 * 100%-stacked + label %. (Sengaja BUKAN pie chart -- dataviz skill:
 * "Part-to-whole -> stacked bar", pie cuma dianjurkan utk 2 slice vs
 * limit/meter.) */
export default function ClassProportionBar({ cameraId, date, zoneType }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await getStatsSummary(cameraId, { date, zoneType });
        if (!cancelled) setSummary(data);
      } catch {
        // biarkan data lama tampil kalau request gagal sementara
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

  const total = summary?.total ?? 0;

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">
        Proporsi Kelas{date ? ` — ${date}` : " Hari Ini"}
      </h3>

      {!summary || total === 0 ? (
        <div className="h-10 flex items-center justify-center text-slate-400 text-sm">
          {loading ? "Memuat…" : "Belum ada data"}
        </div>
      ) : (
        <>
          <div className="flex h-8 rounded-lg overflow-hidden transition-opacity" style={{ opacity: loading ? 0.6 : 1 }}>
            {VEHICLE_CLASSES.map((c, i) => {
              const value = summary[c.key] ?? 0;
              if (value === 0) return null;
              const pct = (value / total) * 100;
              return (
                <div
                  key={c.key}
                  className="h-full flex items-center justify-center text-white text-[11px] font-semibold"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: c.color,
                    marginLeft: i === 0 ? 0 : 2, // surface gap antar segmen
                  }}
                  title={`${c.label}: ${value} (${pct.toFixed(1)}%)`}
                >
                  {pct >= 8 ? `${Math.round(pct)}%` : ""}
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 justify-center mt-3">
            {VEHICLE_CLASSES.map((c) => (
              <span key={c.key} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: c.color }} />
                {c.icon} {c.label} <span className="text-slate-400 tabular-nums">({summary[c.key] ?? 0})</span>
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
