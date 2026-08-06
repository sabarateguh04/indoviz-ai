import AlertPanel from "./AlertPanel.jsx";
import FilterBar from "./FilterBar.jsx";
import StatsSidebar from "./StatsSidebar.jsx";
import TimeSeriesChart from "./TimeSeriesChart.jsx";
import VolumeChart from "./VolumeChart.jsx";

/** Halaman "Analitik" -- semua filter & breakdown detail (dipisah dari
 * halaman Utama yang fokus live view aja). */
export default function AnalyticsPage({
  cameras,
  statsCameraId,
  onChangeCamera,
  statsDate,
  onChangeDate,
  statsZoneType,
  onChangeZoneType,
  alerts,
  zoneTypeById,
  cameraNameById,
}) {
  return (
    <div className="flex-1 overflow-y-auto p-3">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[18rem_1fr] gap-3 items-start">
        <div className="flex flex-col gap-3">
          <FilterBar
            cameras={cameras}
            cameraId={statsCameraId}
            onChangeCamera={onChangeCamera}
            date={statsDate}
            onChangeDate={onChangeDate}
            zoneType={statsZoneType}
            onChangeZoneType={onChangeZoneType}
          />
          <StatsSidebar cameraId={statsCameraId} date={statsDate} zoneType={statsZoneType} />
          <AlertPanel
            liveAlerts={alerts}
            cameraId={statsCameraId}
            date={statsDate}
            zoneType={statsZoneType}
            zoneTypeById={zoneTypeById}
            cameraNameById={cameraNameById}
          />
        </div>

        <div className="flex flex-col gap-3 min-w-0">
          <TimeSeriesChart cameraId={statsCameraId} zoneType={statsZoneType} />
          <VolumeChart cameraId={statsCameraId} date={statsDate} zoneType={statsZoneType} />
        </div>
      </div>
    </div>
  );
}
