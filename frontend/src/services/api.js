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
export const setCameraViewEnabled = (id, viewEnabled) =>
  updateCamera(id, { view_enabled: viewEnabled });

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
// `filters` opsional: { date: "YYYY-MM-DD", zoneType: "counting" | "no_parking" | "direction" | "lane" }
function filterParams({ date, zoneType } = {}) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (zoneType) params.set("zone_type", zoneType);
  return params.toString();
}

export const getStatsSummary = (cameraId, filters = {}) => {
  const params = new URLSearchParams(filterParams(filters));
  if (cameraId) params.set("camera_id", cameraId);
  const qs = params.toString();
  return request(`/stats/summary${qs ? `?${qs}` : ""}`);
};

export const getStatsVolume = (cameraId, hours = 24, filters = {}) => {
  const params = new URLSearchParams(filterParams(filters));
  params.set("hours", hours);
  if (cameraId) params.set("camera_id", cameraId);
  return request(`/stats/volume?${params.toString()}`);
};

export const getAlerts = (cameraId, limit = 50, filters = {}) => {
  const params = new URLSearchParams(filterParams(filters));
  params.set("limit", limit);
  if (cameraId) params.set("camera_id", cameraId);
  return request(`/stats/alerts?${params.toString()}`);
};

// ---- Pengaturan (model YOLO) ----
export const getModelSettings = () => request("/settings/model");
export const setModelSettings = (modelName) =>
  request("/settings/model", { method: "PUT", body: JSON.stringify({ model_name: modelName }) });
