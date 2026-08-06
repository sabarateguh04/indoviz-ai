import { useEffect, useState } from "react";
import AnalyticsPage from "./components/AnalyticsPage.jsx";
import CameraManager from "./components/CameraManager.jsx";
import DatasetPage from "./components/DatasetPage.jsx";
import DetectionEventsModal from "./components/DetectionEventsModal.jsx";
import HomePage from "./components/HomePage.jsx";
import TopBar from "./components/TopBar.jsx";
import ZoneEditor from "./components/ZoneEditor.jsx";
import useCameraSocket from "./hooks/useCameraSocket.js";
import { getCameras, getZones, setCameraViewEnabled } from "./services/api.js";

const CAMERA_POLL_MS = 5000;
const ZONES_POLL_MS = 10000;

export default function App() {
  const [page, setPage] = useState("utama"); // "utama" | "analitik"
  const [cameras, setCameras] = useState([]);
  const [zonesByCamera, setZonesByCamera] = useState({});
  const [view, setView] = useState("2x2");
  const [managerOpen, setManagerOpen] = useState(false);
  const [eventsOpen, setEventsOpen] = useState(false);
  const [zoningCamera, setZoningCamera] = useState(null);
  const [statsCameraId, setStatsCameraId] = useState(null); // null = semua kamera
  const [statsDate, setStatsDate] = useState(null); // null = live/hari ini
  const [statsZoneType, setStatsZoneType] = useState(null); // null = semua tipe zona

  const { framesByCamera, alerts, connected } = useCameraSocket();

  async function refreshCameras() {
    try {
      const data = await getCameras();
      setCameras(data);
    } catch {
      // biarkan daftar lama tampil kalau refresh gagal sementara
    }
  }

  async function refreshZones() {
    try {
      const data = await getZones();
      const grouped = {};
      for (const zone of data) {
        (grouped[zone.camera_id] ??= []).push(zone);
      }
      setZonesByCamera(grouped);
    } catch {
      // biarkan data lama tampil kalau refresh gagal sementara
    }
  }

  useEffect(() => {
    refreshCameras();
    refreshZones();
    const cameraTimer = setInterval(refreshCameras, CAMERA_POLL_MS);
    const zoneTimer = setInterval(refreshZones, ZONES_POLL_MS);
    return () => {
      clearInterval(cameraTimer);
      clearInterval(zoneTimer);
    };
  }, []);

  async function handleToggleView(camera) {
    const next = !(camera.view_enabled !== false);
    setCameras((prev) => prev.map((c) => (c.id === camera.id ? { ...c, view_enabled: next } : c)));
    try {
      await setCameraViewEnabled(camera.id, next);
    } catch {
      refreshCameras(); // gagal -> sinkronkan ulang ke state server yang sebenarnya
    }
  }

  function handleCloseZoneEditor() {
    setZoningCamera(null);
    refreshZones();
  }

  const cameraNameById = Object.fromEntries(cameras.map((c) => [c.id, c.nama]));
  const zoneTypeById = Object.fromEntries(
    Object.values(zonesByCamera)
      .flat()
      .map((z) => [z.id, z.tipe_zona])
  );

  return (
    <div className="h-screen flex flex-col">
      <TopBar
        connected={connected}
        page={page}
        onChangePage={setPage}
        view={view}
        onChangeView={setView}
        onOpenManager={() => setManagerOpen(true)}
        onOpenEvents={() => setEventsOpen(true)}
      />

      {page === "utama" && (
        <HomePage
          cameras={cameras}
          framesByCamera={framesByCamera}
          zonesByCamera={zonesByCamera}
          view={view}
          onSelectCamera={setZoningCamera}
          onToggleView={handleToggleView}
        />
      )}

      {page === "analitik" && (
        <AnalyticsPage
          cameras={cameras}
          statsCameraId={statsCameraId}
          onChangeCamera={setStatsCameraId}
          statsDate={statsDate}
          onChangeDate={setStatsDate}
          statsZoneType={statsZoneType}
          onChangeZoneType={setStatsZoneType}
          alerts={alerts}
          zoneTypeById={zoneTypeById}
          cameraNameById={cameraNameById}
        />
      )}

      {page === "dataset" && <DatasetPage cameraNameById={cameraNameById} />}

      {managerOpen && (
        <CameraManager cameras={cameras} onClose={() => setManagerOpen(false)} onChanged={refreshCameras} />
      )}

      {zoningCamera && <ZoneEditor camera={zoningCamera} onClose={handleCloseZoneEditor} />}

      {eventsOpen && (
        <DetectionEventsModal
          cameraId={statsCameraId}
          date={statsDate}
          zoneType={statsZoneType}
          cameraNameById={cameraNameById}
          onClose={() => setEventsOpen(false)}
        />
      )}
    </div>
  );
}
