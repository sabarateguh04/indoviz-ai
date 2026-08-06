import { useEffect, useState } from "react";
import CameraCard from "./CameraCard.jsx";

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

  const renderCard = (camera) => (
    <CameraCard
      key={camera.id}
      camera={camera}
      frameData={framesByCamera[camera.id]}
      zones={zonesByCamera[camera.id] || []}
      onSelect={onSelectCamera}
      onToggleView={onToggleView}
    />
  );

  if (view === "single") {
    const main = cameras.find((c) => c.id === mainId) || cameras[0];
    return (
      <div className="flex flex-col h-full gap-2">
        <div className="flex-1">{renderCard(main)}</div>
        {cameras.length > 1 && (
          <div className="flex gap-2 overflow-x-auto">
            {cameras.map((c) => (
              <button
                key={c.id}
                onClick={() => setMainId(c.id)}
                className={`shrink-0 w-32 text-xs px-2 py-1 rounded border ${
                  c.id === main.id
                    ? "border-brand-500 bg-brand-50 font-semibold"
                    : "border-slate-300 bg-white"
                }`}
              >
                {c.nama}
              </button>
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
        <div
          className="col-span-3 row-span-3 cursor-pointer"
          onClick={() => onSelectCamera?.(main)}
        >
          {renderCard(main)}
        </div>
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
      {cameras.slice(0, 4).map(renderCard)}
    </div>
  );
}
