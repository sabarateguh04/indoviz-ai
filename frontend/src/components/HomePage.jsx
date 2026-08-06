import CameraGrid from "./CameraGrid.jsx";
import TotalsStrip from "./TotalsStrip.jsx";

/** Halaman "Utama" -- sengaja dibikin fokus cuma ke live view + ringkasan
 * total (dgn ikon), tanpa filter/grafik detail (itu ada di halaman
 * "Analitik") supaya halaman ini ringan & cepat dilihat sekilas. */
export default function HomePage({ cameras, framesByCamera, zonesByCamera, view, onSelectCamera, onToggleView }) {
  return (
    <div className="flex-1 flex flex-col gap-3 p-3 overflow-hidden">
      <TotalsStrip />
      <div className="flex-1 min-h-0">
        <CameraGrid
          cameras={cameras}
          framesByCamera={framesByCamera}
          zonesByCamera={zonesByCamera}
          view={view}
          onSelectCamera={onSelectCamera}
          onToggleView={onToggleView}
        />
      </div>
    </div>
  );
}
