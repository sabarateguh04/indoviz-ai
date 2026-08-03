import { useEffect, useState } from "react";
import { getAlerts } from "../services/api.js";

const TIPE_META = {
  wrong_way: { label: "Lawan Arah", color: "bg-red-100 text-red-700", icon: "⚠️" },
  illegal_parking: { label: "Parkir Liar", color: "bg-amber-100 text-amber-700", icon: "🅿️" },
  lane_violation: { label: "Pelanggaran Jalur", color: "bg-purple-100 text-purple-700", icon: "🚧" },
};

export default function AlertPanel({ liveAlerts = [], cameraId, cameraNameById = {} }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    let cancelled = false;
    getAlerts(cameraId, 30)
      .then((rows) => {
        if (!cancelled) setHistory(rows.map((h) => ({ ...h, id: `hist-${h.id}` })));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  const live = liveAlerts.filter((a) => !cameraId || a.camera_id === cameraId);
  const seen = new Set();
  const list = [];
  for (const a of [...live, ...history]) {
    if (seen.has(a.id)) continue;
    seen.add(a.id);
    list.push(a);
    if (list.length >= 30) break;
  }

  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-4 flex flex-col">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">Alert Terbaru</h3>
      <div className="flex-1 overflow-y-auto space-y-2 max-h-80">
        {list.length === 0 && (
          <div className="text-slate-400 text-sm text-center py-6">Belum ada alert</div>
        )}
        {list.map((a) => {
          const meta = TIPE_META[a.tipe] || { label: a.tipe, color: "bg-slate-100 text-slate-700", icon: "🔔" };
          return (
            <div key={a.id} className={`rounded-lg px-3 py-2 text-sm ${meta.color}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold whitespace-nowrap">
                  {meta.icon} {meta.label}
                </span>
                <span className="text-xs opacity-70 truncate">
                  {cameraNameById[a.camera_id] || `Kamera #${a.camera_id}`}
                </span>
              </div>
              {a.pesan && <div className="text-xs opacity-80 mt-0.5">{a.pesan}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
