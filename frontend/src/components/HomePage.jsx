import AlertPanel from "./AlertPanel.jsx";
import CameraGrid from "./CameraGrid.jsx";
import TotalsStrip from "./TotalsStrip.jsx";

/** Halaman "Utama" -- fokus live view + ringkasan cepat (total hari ini,
 * alert terbaru), tanpa filter/grafik detail (itu ada di halaman
 * "Analitik") supaya halaman ini ringan & cepat dilihat sekilas. */
export default function HomePage({
  cameras,
  framesByCamera,
  zonesByCamera,
  view,
  onSelectCamera,
  onToggleView,
  alerts,
  cameraNameById,
  zoneTypeById,
}) {
  return (
    <div className="flex-1 flex flex-col gap-3 p-3 overflow-hidden">
      <TotalsStrip />
      <div className="flex-1 flex gap-3 min-h-0">
        <div className="flex-1 min-w-0">
          <CameraGrid
            cameras={cameras}
            framesByCamera={framesByCamera}
            zonesByCamera={zonesByCamera}
            view={view}
            onSelectCamera={onSelectCamera}
            onToggleView={onToggleView}
          />
        </div>
        <div className="w-72 shrink-0 overflow-y-auto">
          <AlertPanel liveAlerts={alerts} cameraNameById={cameraNameById} zoneTypeById={zoneTypeById} />
        </div>
      </div>
    </div>
  );
}
