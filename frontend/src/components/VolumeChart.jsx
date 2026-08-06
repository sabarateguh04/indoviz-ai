import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getStatsVolume } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 30000;
const SURFACE = "#ffffff"; // warna kartu -- dipakai sbg "surface gap" 2px antar segmen stacked bar

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => p.value > 0).sort((a, b) => b.value - a.value);
  const total = payload.reduce((sum, p) => sum + (p.value || 0), 0);
  if (rows.length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow-lg border border-slate-200 px-3 py-2 text-sm min-w-[9rem]">
      <div className="text-xs font-semibold text-slate-500 mb-1.5">Jam {label}</div>
      <div className="space-y-1">
        {rows.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-0.5 rounded-full" style={{ backgroundColor: p.color }} />
              {p.name}
            </span>
            <span className="font-semibold text-slate-800 tabular-nums">{p.value}</span>
          </div>
        ))}
      </div>
      <div className="mt-1.5 pt-1.5 border-t border-slate-100 flex items-center justify-between gap-4">
        <span className="text-slate-500">Total</span>
        <span className="font-semibold text-slate-800 tabular-nums">{total}</span>
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 justify-center mt-1">
      {VEHICLE_CLASSES.map((c) => (
        <span key={c.key} className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: c.color }} />
          {c.label}
        </span>
      ))}
    </div>
  );
}

export default function VolumeChart({ cameraId, date, zoneType }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const rows = await getStatsVolume(cameraId, 24, { date, zoneType });
        if (!cancelled) setData(rows);
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

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">
        Volume Kendaraan per Jam{date ? ` — ${date}` : ""}
      </h3>
      <div className="h-64 transition-opacity" style={{ opacity: loading && data.length > 0 ? 0.6 : 1 }}>
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-sm">
            {loading ? "Memuat…" : "Belum ada data volume"}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="jam"
                fontSize={11}
                stroke="#94a3b8"
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                interval="preserveStartEnd"
                minTickGap={20}
              />
              <YAxis
                fontSize={11}
                stroke="#94a3b8"
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                width={28}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f1f5f9" }} />
              {VEHICLE_CLASSES.map((c, i) => (
                <Bar
                  key={c.key}
                  dataKey={c.key}
                  name={c.label}
                  stackId="v"
                  fill={c.color}
                  stroke={SURFACE}
                  strokeWidth={2}
                  radius={i === VEHICLE_CLASSES.length - 1 ? [4, 4, 0, 0] : 0}
                  maxBarSize={24}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <Legend />
    </div>
  );
}
