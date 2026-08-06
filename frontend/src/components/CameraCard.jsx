import { useEffect, useRef, useState } from "react";
import { cameraStatus } from "../lib/cameraStatus.js";
import { VEHICLE_CLASS_COLORS } from "../lib/vehicleClasses.js";

const ZONE_COLORS = {
  counting: "#2563eb",
  no_parking: "#dc2626",
  direction: "#16a34a",
  lane: "#a855f7",
};

function drawZones(ctx, zones) {
  for (const zone of zones) {
    const color = ZONE_COLORS[zone.tipe_zona] || "#64748b";
    ctx.strokeStyle = color;
    ctx.fillStyle = `${color}22`;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    zone.koordinat.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function drawDetections(ctx, detections) {
  for (const det of detections) {
    const [x1, y1, x2, y2] = det.bbox;
    const color = VEHICLE_CLASS_COLORS[det.kelas] || "#22c55e";

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    const label = `${det.kelas} #${det.track_id}${det.kecepatan_kmh ? ` ${det.kecepatan_kmh}km/h` : ""}`;
    ctx.font = "14px sans-serif";
    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = color;
    ctx.fillRect(x1, Math.max(0, y1 - 18), textWidth + 6, 18);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 + 3, Math.max(12, y1 - 5));
  }
}

function drawOverlay(canvas, frameData, zones, showZones) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (showZones && zones?.length) drawZones(ctx, zones);
  if (frameData?.detections) drawDetections(ctx, frameData.detections);
}

function IconButton({ title, active, onClick, children }) {
  return (
    <button
      title={title}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`w-7 h-7 flex items-center justify-center rounded text-xs ${
        active ? "bg-brand-600 text-white" : "bg-black/60 text-white hover:bg-black/80"
      }`}
    >
      {children}
    </button>
  );
}

export default function CameraCard({ camera, frameData, zones = [], onSelect, onToggleView, fill = false }) {
  const canvasRef = useRef(null);
  const [showZones, setShowZones] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frameData) return;
    canvas.width = frameData.frame_width || canvas.width;
    canvas.height = frameData.frame_height || canvas.height;
    drawOverlay(canvas, frameData, zones, showZones);
  }, [frameData, zones, showZones]);

  const status = cameraStatus(camera.status);
  const viewEnabled = camera.view_enabled !== false;

  return (
    <div
      className={`relative bg-slate-900 rounded-xl overflow-hidden shadow border border-slate-200 cursor-pointer ${
        fill ? "w-full h-full" : "aspect-video"
      }`}
      onClick={() => onSelect?.(camera)}
    >
      {viewEnabled && frameData?.frame_jpeg_b64 ? (
        <img
          src={`data:image/jpeg;base64,${frameData.frame_jpeg_b64}`}
          alt={camera.nama}
          className="absolute inset-0 w-full h-full object-contain"
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-slate-400 text-sm text-center px-4">
          {!viewEnabled ? (
            <>
              <span>Live view dimatikan</span>
              <span className="text-xs text-slate-500">Counting & analitik tetap berjalan di background</span>
            </>
          ) : camera.status === "offline" ? (
            "Kamera offline"
          ) : (
            "Menunggu stream..."
          )}
        </div>
      )}

      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full object-contain pointer-events-none" />

      {camera.status === "online" && (
        <span className="absolute top-2 left-2 flex items-center gap-1 bg-red-600/90 text-white text-xs font-bold px-2 py-0.5 rounded">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> REC
        </span>
      )}

      <div className="absolute top-2 right-2 flex items-center gap-1.5">
        {frameData?.fps !== undefined && viewEnabled && (
          <span className="bg-black/60 text-white text-xs px-2 py-0.5 rounded font-mono">
            {frameData.fps.toFixed(1)} fps
          </span>
        )}
        <IconButton
          title={showZones ? "Sembunyikan poligon zona" : "Tampilkan poligon zona"}
          active={showZones}
          onClick={() => setShowZones((v) => !v)}
        >
          {showZones ? "◎" : "◇"}
        </IconButton>
        {fill ? (
          <button
            title="Counting & analitik tetap berjalan di background walau live view dimatikan"
            onClick={(e) => {
              e.stopPropagation();
              onToggleView?.(camera);
            }}
            className={`h-7 flex items-center gap-1.5 px-2.5 rounded text-xs font-medium ${
              !viewEnabled ? "bg-brand-600 text-white" : "bg-black/60 text-white hover:bg-black/80"
            }`}
          >
            <span>{viewEnabled ? "❚❚" : "▶"}</span>
            {viewEnabled ? "Matikan live view" : "Nyalakan live view"}
          </button>
        ) : (
          <IconButton
            title={viewEnabled ? "Matikan live view (hemat bandwidth)" : "Nyalakan live view"}
            active={!viewEnabled}
            onClick={() => onToggleView?.(camera)}
          >
            {viewEnabled ? "❚❚" : "▶"}
          </IconButton>
        )}
      </div>

      <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-xs px-2 py-1 flex items-center justify-between">
        <span className="font-medium truncate">{camera.nama}</span>
        <span className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          {status.text}
        </span>
      </div>
    </div>
  );
}
