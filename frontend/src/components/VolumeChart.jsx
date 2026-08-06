import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getStatsVolume } from "../services/api.js";

const REFRESH_MS = 30000;

const SERIES = [
  { key: "motor", color: "#f59e0b", label: "Motor" },
  { key: "mobil", color: "#2563eb", label: "Mobil" },
  { key: "bus", color: "#7c3aed", label: "Bus" },
  { key: "truk", color: "#dc2626", label: "Truk" },
];

export default function VolumeChart({ cameraId, date, zoneType }) {
  const [data, setData] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const rows = await getStatsVolume(cameraId, 24, { date, zoneType });
        if (!cancelled) setData(rows);
      } catch {
        // biarkan data lama tampil kalau request gagal sementara
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
      <div className="h-64">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-sm">
            Belum ada data volume
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="jam" fontSize={12} />
              <YAxis fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Legend />
              {SERIES.map((s) => (
                <Bar key={s.key} dataKey={s.key} name={s.label} stackId="v" fill={s.color} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
