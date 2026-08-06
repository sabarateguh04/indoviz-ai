import { useEffect, useState } from "react";
import AlertPanel from "./components/AlertPanel.jsx";
import CameraGrid from "./components/CameraGrid.jsx";
import CameraManager from "./components/CameraManager.jsx";
import StatsSidebar from "./components/StatsSidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import VolumeChart from "./components/VolumeChart.jsx";
import ZoneEditor from "./components/ZoneEditor.jsx";
import useCameraSocket from "./hooks/useCameraSocket.js";
import { getCameras, getZones, setCameraViewEnabled } from "./services/api.js";

const CAMERA_POLL_MS = 5000;
const ZONES_POLL_MS = 10000;

export default function App() {
  const [cameras, setCameras] = useState([]);
  const [zonesByCamera, setZonesByCamera] = useState({});
  const [view, setView] = useState("2x2");
  const [managerOpen, setManagerOpen] = useState(false);
  const [zoningCamera, setZoningCamera] = useState(null);
  const [statsCameraId, setStatsCameraId] = useState(null); // null = semua kamera

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

  return (
    <div className="h-screen flex flex-col">
      <TopBar
        connected={connected}
        view={view}
        onChangeView={setView}
        onOpenManager={() => setManagerOpen(true)}
      />

      <div className="flex-1 flex gap-3 p-3 overflow-hidden">
        <div className="flex-1 min-w-0">
          <CameraGrid
            cameras={cameras}
            framesByCamera={framesByCamera}
            zonesByCamera={zonesByCamera}
            view={view}
            onSelectCamera={setZoningCamera}
            onToggleView={handleToggleView}
          />
        </div>

        <div className="w-80 shrink-0 flex flex-col gap-3 overflow-y-auto">
          <div className="bg-white rounded-xl shadow border border-slate-200 p-3">
            <label className="block text-xs font-semibold text-slate-500 mb-1">Tampilkan Statistik Untuk</label>
            <select
              value={statsCameraId ?? ""}
              onChange={(e) => setStatsCameraId(e.target.value ? Number(e.target.value) : null)}
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

          <StatsSidebar cameraId={statsCameraId} />
          <VolumeChart cameraId={statsCameraId} />
          <AlertPanel liveAlerts={alerts} cameraId={statsCameraId} cameraNameById={cameraNameById} />
        </div>
      </div>

      {managerOpen && (
        <CameraManager cameras={cameras} onClose={() => setManagerOpen(false)} onChanged={refreshCameras} />
      )}

      {zoningCamera && <ZoneEditor camera={zoningCamera} onClose={handleCloseZoneEditor} />}
    </div>
  );
}
