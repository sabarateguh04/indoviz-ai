import { useEffect, useState } from "react";
import { getStatsSummary } from "../services/api.js";

const KELAS_LABEL = { motor: "Motor", mobil: "Mobil", bus: "Bus", truk: "Truk", tidak_diketahui: "Tidak Diketahui" };
const REFRESH_MS = 10000;

export default function StatsSidebar({ cameraId, date, zoneType }) {
  const [summary, setSummary] = useState({ motor: 0, mobil: 0, bus: 0, truk: 0, tidak_diketahui: 0, total: 0 });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getStatsSummary(cameraId, { date, zoneType });
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
  }, [cameraId, date, zoneType]);

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">{date ? `Total Tanggal ${date}` : "Total Hari Ini"}</h3>
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(KELAS_LABEL).map(([key, label]) => {
          const unknown = key === "tidak_diketahui";
          return (
            <div
              key={key}
              className={`rounded-lg p-3 text-center ${unknown ? "col-span-2 bg-slate-100" : "bg-brand-50"}`}
            >
              <div className={`text-2xl font-bold ${unknown ? "text-slate-500" : "text-brand-700"}`}>
                {summary[key] ?? 0}
              </div>
              <div className="text-xs text-slate-500">{label}</div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-sm">
        <span className="text-slate-500">Total kendaraan</span>
        <span className="font-bold text-slate-800">{summary.total ?? 0}</span>
      </div>
    </div>
  );
}
