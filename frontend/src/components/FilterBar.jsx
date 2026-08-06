const ZONE_TYPE_OPTIONS = [
  { value: "", label: "Semua Tipe Zona" },
  { value: "counting", label: "Counting" },
  { value: "no_parking", label: "Larangan Parkir" },
  { value: "direction", label: "Arah (Lawan Arah)" },
  { value: "lane", label: "Jalur" },
];

/** Filter untuk StatsSidebar/VolumeChart/AlertPanel: kamera, tanggal,
 * dan tipe zona. `date` null berarti "hari ini/live", string "" dari
 * <input type="date"> dinormalisasi jadi null juga. */
export default function FilterBar({
  cameras,
  cameraId,
  onChangeCamera,
  date,
  onChangeDate,
  zoneType,
  onChangeZoneType,
}) {
  return (
    <div className="bg-white rounded-xl shadow border border-slate-200 p-3 space-y-2.5">
      <div>
        <label className="block text-xs font-semibold text-slate-500 mb-1">Kamera</label>
        <select
          value={cameraId ?? ""}
          onChange={(e) => onChangeCamera(e.target.value ? Number(e.target.value) : null)}
          className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm"
        >
          <option value="">Semua Kamera</option>
          {cameras.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nama}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-500 mb-1">Tanggal</label>
        <div className="flex gap-1.5">
          <input
            type="date"
            value={date ?? ""}
            onChange={(e) => onChangeDate(e.target.value || null)}
            className="flex-1 min-w-0 border border-slate-300 rounded-lg px-2 py-1.5 text-sm"
          />
          {date && (
            <button
              onClick={() => onChangeDate(null)}
              title="Kembali ke live/hari ini"
              className="shrink-0 px-2 rounded-lg border border-slate-300 text-xs text-slate-500 hover:bg-slate-50"
            >
              Live
            </button>
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-500 mb-1">Tipe Zona</label>
        <select
          value={zoneType ?? ""}
          onChange={(e) => onChangeZoneType(e.target.value || null)}
          className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm"
        >
          {ZONE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
