import { useEffect, useRef } from "react";

const CLASS_COLORS = {
  motor: "#f59e0b",
  mobil: "#2563eb",
  bus: "#7c3aed",
  truk: "#dc2626",
};

const STATUS_LABEL = {
  online: { text: "Online", dot: "bg-emerald-400" },
  warning: { text: "Warning", dot: "bg-amber-400" },
  offline: { text: "Offline", dot: "bg-red-400" },
};

function drawOverlay(canvas, frameData) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!frameData?.detections) return;

  for (const det of frameData.detections) {
    const [x1, y1, x2, y2] = det.bbox;
    const color = CLASS_COLORS[det.kelas] || "#22c55e";

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

export default function CameraCard({ camera, frameData, onSelect }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frameData) return;
    canvas.width = frameData.frame_width || canvas.width;
    canvas.height = frameData.frame_height || canvas.height;
    drawOverlay(canvas, frameData);
  }, [frameData]);

  const status = STATUS_LABEL[camera.status] || STATUS_LABEL.offline;

  return (
    <div
      className="relative bg-slate-900 rounded-xl overflow-hidden shadow border border-slate-200 aspect-video cursor-pointer"
      onClick={() => onSelect?.(camera)}
    >
      {frameData?.frame_jpeg_b64 ? (
        <img
          src={`data:image/jpeg;base64,${frameData.frame_jpeg_b64}`}
          alt={camera.nama}
          className="absolute inset-0 w-full h-full object-contain"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
          {camera.status === "offline" ? "Kamera offline" : "Menunggu stream..."}
        </div>
      )}

      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />

      {camera.status === "online" && (
        <span className="absolute top-2 left-2 flex items-center gap-1 bg-red-600/90 text-white text-xs font-bold px-2 py-0.5 rounded">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> REC
        </span>
      )}

      {frameData?.fps !== undefined && (
        <span className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded font-mono">
          {frameData.fps.toFixed(1)} fps
        </span>
      )}

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
