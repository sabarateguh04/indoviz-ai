import { useEffect, useState } from "react";
import CameraCard from "./CameraCard.jsx";
import { cameraStatus } from "../lib/cameraStatus.js";

function CameraPickerButton({ camera, active, onClick }) {
  const status = cameraStatus(camera.status);
  return (
    <button
      onClick={onClick}
      className={`shrink-0 w-36 text-left text-xs px-2.5 py-2 rounded-lg border transition ${
        active ? "border-brand-500 bg-brand-50 font-semibold text-brand-700" : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <div className="flex items-center gap-1.5 truncate">
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${status.dot}`} />
        <span className="truncate">{camera.nama}</span>
      </div>
      <span className={`text-[11px] font-normal ${active ? "text-brand-500" : "text-slate-400"}`}>{status.text}</span>
    </button>
  );
}

export default function CameraGrid({ cameras, framesByCamera, zonesByCamera = {}, view, onSelectCamera, onToggleView }) {
  const [mainId, setMainId] = useState(cameras[0]?.id);

  useEffect(() => {
    if (!cameras.some((c) => c.id === mainId)) {
      setMainId(cameras[0]?.id);
    }
  }, [cameras, mainId]);

  if (cameras.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        Belum ada kamera. Klik "Kelola Kamera" untuk menambahkan.
      </div>
    );
  }

  const renderCard = (camera, fill = false) => (
    <CameraCard
      key={camera.id}
      camera={camera}
      frameData={framesByCamera[camera.id]}
      zones={zonesByCamera[camera.id] || []}
      onSelect={onSelectCamera}
      onToggleView={onToggleView}
      fill={fill}
    />
  );

  if (view === "single") {
    const main = cameras.find((c) => c.id === mainId) || cameras[0];
    return (
      <div className="flex flex-col h-full gap-2">
        <div className="flex-1 min-h-0">{renderCard(main, true)}</div>
        {cameras.length > 1 && (
          <div className="shrink-0 flex gap-2 overflow-x-auto pb-1">
            {cameras.map((c) => (
              <CameraPickerButton key={c.id} camera={c} active={c.id === main.id} onClick={() => setMainId(c.id)} />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (view === "wide") {
    return (
      <div className="flex flex-col gap-3 overflow-y-auto h-full">
        {cameras.map((c) => (
          <div key={c.id} className="w-full">
            {renderCard(c)}
          </div>
        ))}
      </div>
    );
  }

  if (view === "1+3") {
    const main = cameras.find((c) => c.id === mainId) || cameras[0];
    const others = cameras.filter((c) => c.id !== main.id);
    return (
      <div className="grid grid-cols-4 grid-rows-3 gap-2 h-full">
        <div className="col-span-3 row-span-3 min-h-0">{renderCard(main, true)}</div>
        <div className="col-span-1 row-span-3 flex flex-col gap-2 overflow-y-auto">
          {others.map((c) => (
            <div key={c.id} onClick={() => setMainId(c.id)}>
              {renderCard(c)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // default: "2x2"
  return (
    <div className="grid grid-cols-2 grid-rows-2 gap-2 h-full">
      {cameras.slice(0, 4).map((c) => renderCard(c))}
    </div>
  );
}
