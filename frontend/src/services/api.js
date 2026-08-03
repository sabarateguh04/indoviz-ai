const BASE_URL = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request gagal: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---- Kamera ----
export const getCameras = () => request("/cameras");
export const getCamera = (id) => request(`/cameras/${id}`);
export const createCamera = (data) =>
  request("/cameras", { method: "POST", body: JSON.stringify(data) });
export const updateCamera = (id, data) =>
  request(`/cameras/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteCamera = (id) =>
  request(`/cameras/${id}`, { method: "DELETE" });
export const testCameraConnection = (rtsp_url) =>
  request("/cameras/test-connection", {
    method: "POST",
    body: JSON.stringify({ rtsp_url }),
  });

// ---- Zona ----
export const getZones = (cameraId) =>
  request(cameraId ? `/zones?camera_id=${cameraId}` : "/zones");
export const createZone = (data) =>
  request("/zones", { method: "POST", body: JSON.stringify(data) });
export const updateZone = (id, data) =>
  request(`/zones/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteZone = (id) =>
  request(`/zones/${id}`, { method: "DELETE" });

// ---- Snapshot ----
export const getSnapshotUrl = (cameraId) =>
  `${BASE_URL}/snapshot/${cameraId}?t=${Date.now()}`;

// ---- Statistik ----
export const getStatsSummary = (cameraId) =>
  request(cameraId ? `/stats/summary?camera_id=${cameraId}` : "/stats/summary");
export const getStatsVolume = (cameraId, hours = 24) =>
  request(
    `/stats/volume?hours=${hours}${cameraId ? `&camera_id=${cameraId}` : ""}`
  );
export const getAlerts = (cameraId, limit = 50) =>
  request(
    `/stats/alerts?limit=${limit}${cameraId ? `&camera_id=${cameraId}` : ""}`
  );
