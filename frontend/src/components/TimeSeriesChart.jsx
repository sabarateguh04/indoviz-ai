import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getStatsTimeseries } from "../services/api.js";
import { VEHICLE_CLASSES } from "../lib/vehicleClasses.js";

const REFRESH_MS = 20000;

const GRANULARITY_OPTIONS = [
  { value: "minute", label: "Menit" },
  { value: "hour", label: "Jam" },
  { value: "day", label: "Hari" },
  { value: "week", label: "Minggu" },
  { value: "month", label: "Bulan" },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => p.value > 0).sort((a, b) => b.value - a.value);
  if (rows.length === 0) return null;
  const total = payload.reduce((sum, p) => sum + (p.value || 0), 0);
  return (
    <div className="bg-white rounded-lg shadow-lg border border-slate-200 px-3 py-2 text-sm min-w-[9rem]">
      <div className="text-xs font-semibold text-slate-500 mb-1.5">{label}</div>
      <div className="space-y-1">
        {rows.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="w-2 h-0.5 rounded-full" style={{ backgroundColor: p.stroke }} />
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

/** Grafik tren kendaraan dgn granularitas fleksibel (menit/jam/hari/minggu/
 * bulan) + tabel data yang sama di bawahnya. Beda dari VolumeChart (bar per
 * jam dlm 1 tanggal spesifik) -- ini selalu "N terakhir dari sekarang",
 * dan gak ikut filter tanggal (cuma kamera + tipe zona). */
export default function TimeSeriesChart({ cameraId, zoneType }) {
  const [granularity, setGranularity] = useState("hour");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const data = await getStatsTimeseries(cameraId, { granularity, zoneType });
        if (!cancelled) setRows(data);
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
  }, [cameraId, zoneType, granularity]);

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-slate-500">Tren Kendaraan</h3>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {GRANULARITY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setGranularity(opt.value)}
              className={`px-2.5 py-1 rounded-md text-xs transition ${
                granularity === opt.value ? "bg-white text-brand-700 font-semibold shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="h-56 transition-opacity" style={{ opacity: loading && rows.length > 0 ? 0.6 : 1 }}>
        {rows.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-sm">
            {loading ? "Memuat…" : "Belum ada data"}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="label"
                fontSize={11}
                stroke="#94a3b8"
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis fontSize={11} stroke="#94a3b8" tickLine={false} axisLine={false} allowDecimals={false} width={28} />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#cbd5e1", strokeWidth: 1 }} />
              {VEHICLE_CLASSES.map((c) => (
                <Line
                  key={c.key}
                  type="monotone"
                  dataKey={c.key}
                  name={c.label}
                  stroke={c.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "#ffffff" }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="flex flex-wrap gap-x-3 gap-y-1 justify-center mt-2">
        {VEHICLE_CLASSES.map((c) => (
          <span key={c.key} className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: c.color }} />
            {c.label}
          </span>
        ))}
      </div>

      {rows.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <button onClick={() => setShowTable((v) => !v)} className="text-xs text-brand-600 hover:underline font-medium">
            {showTable ? "▾ Sembunyikan tabel" : "▸ Tampilkan sebagai tabel"}
          </button>
          {showTable && (
            <div className="mt-2 max-h-56 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-50 text-slate-500 text-left">
                  <tr>
                    <th className="px-2 py-1.5 font-semibold">Waktu</th>
                    {VEHICLE_CLASSES.map((c) => (
                      <th key={c.key} className="px-2 py-1.5 font-semibold text-right">
                        {c.icon}
                      </th>
                    ))}
                    <th className="px-2 py-1.5 font-semibold text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[...rows].reverse().map((r) => (
                    <tr key={r.waktu} className="hover:bg-slate-50">
                      <td className="px-2 py-1 text-slate-600 whitespace-nowrap">{r.label}</td>
                      {VEHICLE_CLASSES.map((c) => (
                        <td key={c.key} className="px-2 py-1 text-right tabular-nums text-slate-700">
                          {r[c.key]}
                        </td>
                      ))}
                      <td className="px-2 py-1 text-right tabular-nums font-semibold text-slate-800">{r.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
