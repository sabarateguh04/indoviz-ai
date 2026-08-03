import { useEffect, useState } from "react";
import AlertPanel from "./components/AlertPanel.jsx";
import CameraGrid from "./components/CameraGrid.jsx";
import CameraManager from "./components/CameraManager.jsx";
import StatsSidebar from "./components/StatsSidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import VolumeChart from "./components/VolumeChart.jsx";
import ZoneEditor from "./components/ZoneEditor.jsx";
import useCameraSocket from "./hooks/useCameraSocket.js";
import { getCameras } from "./services/api.js";

const CAMERA_POLL_MS = 5000;

export default function App() {
  const [cameras, setCameras] = useState([]);
  const [view, setView] = useState("2x2");
  const [managerOpen, setManagerOpen] = useState(false);
  const [zoningCamera, setZoningCamera] = useState(null);

  const { framesByCamera, alerts, connected } = useCameraSocket();

  async function refreshCameras() {
    try {
      const data = await getCameras();
      setCameras(data);
    } catch {
      // biarkan daftar lama tampil kalau refresh gagal sementara
    }
  }

  useEffect(() => {
    refreshCameras();
    const timer = setInterval(refreshCameras, CAMERA_POLL_MS);
    return () => clearInterval(timer);
  }, []);

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
            view={view}
            onSelectCamera={setZoningCamera}
          />
        </div>

        <div className="w-80 shrink-0 flex flex-col gap-3 overflow-y-auto">
          <StatsSidebar />
          <VolumeChart />
          <AlertPanel liveAlerts={alerts} cameraNameById={cameraNameById} />
        </div>
      </div>

      {managerOpen && (
        <CameraManager cameras={cameras} onClose={() => setManagerOpen(false)} onChanged={refreshCameras} />
      )}

      {zoningCamera && <ZoneEditor camera={zoningCamera} onClose={() => setZoningCamera(null)} />}
    </div>
  );
}
