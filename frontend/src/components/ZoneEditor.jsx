import { useEffect, useRef, useState } from "react";
import { createZone, deleteZone, getSnapshotUrl, getZones } from "../services/api.js";

const TIPE_OPTIONS = [
  { value: "counting", label: "Counting", color: "#2563eb" },
  { value: "no_parking", label: "Larangan Parkir", color: "#dc2626" },
  { value: "direction", label: "Arah (wrong-way)", color: "#16a34a" },
  { value: "lane", label: "Jalur", color: "#a855f7" },
];

function colorFor(tipe) {
  return TIPE_OPTIONS.find((t) => t.value === tipe)?.color || "#64748b";
}

function polygonCentroid(points) {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  return [xs.reduce((a, b) => a + b, 0) / xs.length, ys.reduce((a, b) => a + b, 0) / ys.length];
}

function angleDeg(from, to) {
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const deg = (Math.atan2(dy, dx) * 180) / Math.PI;
  return (deg + 360) % 360;
}

export default function ZoneEditor({ camera, onClose }) {
  const canvasRef = useRef(null);
  const imgRef = useRef(new Image());
  const [imgLoaded, setImgLoaded] = useState(false);
  const [zones, setZones] = useState([]);
  const [tipeZona, setTipeZona] = useState("counting");
  const [points, setPoints] = useState([]);
  const [awaitingArrow, setAwaitingArrow] = useState(false);
  const [arahNormalDeg, setArahNormalDeg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getZones(camera.id).then(setZones).catch(() => {});
  }, [camera.id]);

  useEffect(() => {
    const img = imgRef.current;
    img.onload = () => setImgLoaded(true);
    img.src = getSnapshotUrl(camera.id);
  }, [camera.id]);

  useEffect(() => {
    redraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imgLoaded, zones, points, awaitingArrow]);

  function redraw() {
    const canvas = canvasRef.current;
    if (!canvas || !imgLoaded) return;
    const img = imgRef.current;
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    for (const zone of zones) {
      drawPolygon(ctx, zone.koordinat, colorFor(zone.tipe_zona), zone.nama || zone.tipe_zona);
    }

    if (points.length > 0) {
      drawPolygon(ctx, points, colorFor(tipeZona), null, !awaitingArrow);
    }
  }

  function drawPolygon(ctx, poly, color, label, openPath = false) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color + "33";
    ctx.lineWidth = 2;
    ctx.beginPath();
    poly.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
    if (!openPath) ctx.closePath();
    ctx.fill();
    ctx.stroke();

    poly.forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    });

    if (label) {
      const [cx, cy] = polygonCentroid(poly);
      ctx.font = "13px sans-serif";
      ctx.fillStyle = color;
      ctx.fillText(label, cx, cy);
    }
  }

  function toImageCoords(e) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return [(e.clientX - rect.left) * scaleX, (e.clientY - rect.top) * scaleY];
  }

  function handleCanvasClick(e) {
    const [x, y] = toImageCoords(e);

    if (awaitingArrow) {
      const centroid = polygonCentroid(points);
      setArahNormalDeg(angleDeg(centroid, [x, y]));
      setAwaitingArrow(false);
      return;
    }

    setPoints((prev) => [...prev, [x, y]]);
  }

  function handleClosePolygon() {
    if (points.length < 3) {
      setError("Poligon minimal harus punya 3 titik");
      return;
    }
    setError(null);
    if (tipeZona === "direction") {
      setAwaitingArrow(true);
    }
  }

  function handleReset() {
    setPoints([]);
    setAwaitingArrow(false);
    setArahNormalDeg(null);
    setError(null);
  }

  async function handleSave() {
    if (points.length < 3) {
      setError("Poligon minimal harus punya 3 titik");
      return;
    }
    if (tipeZona === "direction" && arahNormalDeg === null) {
      setError("Tandai dulu arah panah normal (klik 1 titik arah setelah menutup poligon)");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const zone = await createZone({
        camera_id: camera.id,
        tipe_zona: tipeZona,
        koordinat: points,
        arah_normal_deg: tipeZona === "direction" ? arahNormalDeg : null,
      });
      setZones((prev) => [...prev, zone]);
      handleReset();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteZone(id) {
    try {
      await deleteZone(id);
      setZones((prev) => prev.filter((z) => z.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl p-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-800">Editor Zona — {camera.nama}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            {!imgLoaded ? (
              <div className="aspect-video bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 text-sm">
                Memuat snapshot...
              </div>
            ) : (
              <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                className="w-full rounded-lg border border-slate-300 cursor-crosshair"
              />
            )}
            <p className="text-xs text-slate-500 mt-2">
              Klik untuk menambah titik poligon. Minimal 3 titik, lalu klik "Tutup Poligon".
              {tipeZona === "direction" && " Untuk zona arah, setelah ditutup klik 1 titik lagi untuk menandai arah normal."}
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Tipe Zona Baru</label>
              <select
                value={tipeZona}
                onChange={(e) => {
                  setTipeZona(e.target.value);
                  handleReset();
                }}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              >
                {TIPE_OPTIONS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleClosePolygon}
                className="flex-1 px-3 py-2 rounded-lg text-sm font-semibold border border-brand-500 text-brand-700 hover:bg-brand-50"
              >
                Tutup Poligon
              </button>
              <button
                onClick={handleReset}
                className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Reset
              </button>
            </div>

            {error && <div className="text-sm text-red-600">{error}</div>}

            <button
              onClick={handleSave}
              disabled={saving || points.length < 3}
              className="w-full px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? "Menyimpan..." : "Simpan Zona"}
            </button>

            <div className="pt-3 border-t border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 mb-2">Zona Tersimpan</h3>
              <ul className="space-y-1 max-h-48 overflow-y-auto">
                {zones.length === 0 && <li className="text-xs text-slate-400">Belum ada zona</li>}
                {zones.map((z) => (
                  <li
                    key={z.id}
                    className="flex items-center justify-between text-sm bg-slate-50 rounded px-2 py-1"
                  >
                    <span style={{ color: colorFor(z.tipe_zona) }} className="font-medium">
                      {TIPE_OPTIONS.find((t) => t.value === z.tipe_zona)?.label || z.tipe_zona}
                    </span>
                    <button
                      onClick={() => handleDeleteZone(z.id)}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      Hapus
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
