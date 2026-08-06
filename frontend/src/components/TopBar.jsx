import { useEffect, useState } from "react";
import DisplaySettings from "./DisplaySettings.jsx";
import ModelSelector from "./ModelSelector.jsx";

const PAGES = [
  { value: "utama", label: "Utama" },
  { value: "analitik", label: "Analitik" },
  { value: "dataset", label: "Dataset" },
];

export default function TopBar({ connected, page, onChangePage, view, onChangeView, onOpenManager, onOpenEvents }) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const jam = now.toLocaleTimeString("id-ID", { hour12: false });

  return (
    <header className="flex items-center justify-between bg-brand-700 text-white px-4 py-3 shadow-md flex-wrap gap-y-2">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold tracking-wide">IndoVIS</span>
          <span className="text-sm text-brand-100 hidden sm:inline">Analitik Kamera</span>
        </div>

        <div className="flex items-center gap-1 bg-brand-800/40 rounded-lg p-1">
          {PAGES.map((p) => (
            <button
              key={p.value}
              onClick={() => onChangePage(p.value)}
              className={`px-3 py-1 rounded-md text-sm font-semibold transition ${
                page === p.value ? "bg-white text-brand-700" : "text-white/80 hover:bg-brand-600"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {page === "utama" && (
          <div className="hidden md:flex items-center gap-1 bg-brand-600 rounded-lg p-1">
            {["2x2", "1+3", "wide", "single"].map((v) => (
              <button
                key={v}
                onClick={() => onChangeView(v)}
                className={`px-3 py-1 rounded-md text-sm transition ${
                  view === v ? "bg-white text-brand-700 font-semibold" : "text-white/80 hover:bg-brand-500"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        )}

        <ModelSelector />
        <DisplaySettings />

        <button
          onClick={onOpenEvents}
          className="px-3 py-1.5 rounded-md border border-white/30 text-white text-sm font-semibold hover:bg-brand-600"
        >
          Data Deteksi
        </button>

        <button
          onClick={onOpenManager}
          className="px-3 py-1.5 rounded-md bg-white text-brand-700 text-sm font-semibold hover:bg-brand-50"
        >
          Kelola Kamera
        </button>

        <div className="flex items-center gap-2 text-sm">
          <span
            className={`w-2.5 h-2.5 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`}
            title={connected ? "Backend terhubung" : "Backend terputus"}
          />
          <span className="font-mono">{jam}</span>
        </div>
      </div>
    </header>
  );
}
