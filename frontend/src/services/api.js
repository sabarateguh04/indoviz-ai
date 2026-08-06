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

// `filters` opsional juga menerima { kelas } di samping date/zoneType
export const getStatsEvents = (cameraId, { limit = 50, offset = 0, kelas, ...filters } = {}) => {
  const params = new URLSearchParams(filterParams(filters));
  params.set("limit", limit);
  params.set("offset", offset);
  if (cameraId) params.set("camera_id", cameraId);
  if (kelas) params.set("kelas", kelas);
  return request(`/stats/events?${params.toString()}`);
};

// Hapus event counting sesuai filter -- backend WAJIB minimal 1 filter diisi
export const deleteStatsEvents = (cameraId, { kelas, ...filters } = {}) => {
  const params = new URLSearchParams(filterParams(filters));
  if (cameraId) params.set("camera_id", cameraId);
  if (kelas) params.set("kelas", kelas);
  return request(`/stats/events?${params.toString()}`, { method: "DELETE" });
};

// granularity: "minute" | "hour" | "day" | "week" | "month"
export const getStatsTimeseries = (cameraId, { granularity = "hour", count, zoneType } = {}) => {
  const params = new URLSearchParams();
  params.set("granularity", granularity);
  if (count) params.set("count", count);
  if (zoneType) params.set("zone_type", zoneType);
  if (cameraId) params.set("camera_id", cameraId);
  return request(`/stats/timeseries?${params.toString()}`);
};

// ---- Dataset training (hasil training/collect_frames.py) ----
export const getTrainingFrames = ({ cameraId, labeled, limit = 60, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  params.set("limit", limit);
  params.set("offset", offset);
  if (cameraId) params.set("camera_id", cameraId);
  if (labeled !== undefined && labeled !== null) params.set("labeled", labeled);
  return request(`/training?${params.toString()}`);
};
export const getTrainingFrameImageUrl = (filename) => `${BASE_URL}/training/frames/${encodeURIComponent(filename)}`;
export const deleteTrainingFrame = (filename) =>
  request(`/training/frames/${encodeURIComponent(filename)}`, { method: "DELETE" });

// ---- Pengaturan (model YOLO) ----
export const getModelSettings = () => request("/settings/model");
export const setModelSettings = (modelName) =>
  request("/settings/model", { method: "PUT", body: JSON.stringify({ model_name: modelName }) });

// ---- Pengaturan (kecepatan live view) ----
export const getDisplaySettings = () => request("/settings/display");
export const setDisplaySettings = (wsBroadcastInterval) =>
  request("/settings/display", {
    method: "PUT",
    body: JSON.stringify({ ws_broadcast_interval: wsBroadcastInterval }),
  });
