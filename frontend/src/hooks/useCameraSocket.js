import { useEffect, useRef, useState } from "react";

const RECONNECT_DELAY_MS = 2000;
const MAX_ALERTS = 100;

/**
 * Koneksi WebSocket ke backend (`/ws/live`) untuk data live: bbox tracking,
 * counting, alert, kepadatan per zona — 1 koneksi dipakai untuk semua
 * kamera, dipilah lewat `camera_id` di tiap pesan.
 */
export default function useCameraSocket() {
  const [framesByCamera, setFramesByCamera] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  useEffect(() => {
    let stopped = false;

    function connect() {
      if (stopped) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${protocol}//${window.location.host}/ws/live`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event) => {
        let payload;
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        if (payload.type !== "frame_update") return;

        setFramesByCamera((prev) => ({ ...prev, [payload.camera_id]: payload }));

        if (payload.alerts && payload.alerts.length > 0) {
          setAlerts((prev) => {
            const withTs = payload.alerts.map((a) => ({
              ...a,
              camera_id: payload.camera_id,
              timestamp: payload.timestamp,
              id: `${payload.camera_id}-${a.track_id}-${a.tipe}-${payload.timestamp}`,
            }));
            return [...withTs, ...prev].slice(0, MAX_ALERTS);
          });
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!stopped) {
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      stopped = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return { framesByCamera, alerts, connected };
}
