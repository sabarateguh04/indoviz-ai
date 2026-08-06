/** Status kamera terpusat (dipakai CameraCard & CameraGrid) supaya warna &
 * label konsisten di badge besar maupun strip pemilih kamera kecil. */
export const CAMERA_STATUS = {
  online: { text: "Online", dot: "bg-emerald-400" },
  warning: { text: "Warning", dot: "bg-amber-400" },
  offline: { text: "Offline", dot: "bg-red-400" },
};

export function cameraStatus(status) {
  return CAMERA_STATUS[status] || CAMERA_STATUS.offline;
}
