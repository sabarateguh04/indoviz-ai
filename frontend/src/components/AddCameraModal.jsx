import { useState } from "react";
import { createCamera, testCameraConnection, updateCamera } from "../services/api.js";

export default function AddCameraModal({ camera, onClose, onSaved }) {
  const isEdit = Boolean(camera?.id);
  const [nama, setNama] = useState(camera?.nama || "");
  const [rtspUrl, setRtspUrl] = useState(camera?.rtsp_url || "");
  const [imgsz, setImgsz] = useState(camera?.imgsz || "");
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleTest() {
    if (!rtspUrl) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testCameraConnection(rtspUrl);
      setTestResult(res);
    } catch (err) {
      setTestResult({ berhasil: false, pesan: err.message });
    } finally {
      setTesting(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        nama,
        rtsp_url: rtspUrl,
        imgsz: imgsz ? Number(imgsz) : null,
      };
      const saved = isEdit ? await updateCamera(camera.id, payload) : await createCamera(payload);
      onSaved(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-5">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEdit ? "Edit Kamera" : "Tambah Kamera"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Nama Kamera</label>
            <input
              required
              value={nama}
              onChange={(e) => setNama(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="mis. Simpang Cempaka Putih"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">RTSP URL</label>
            <input
              required
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="rtsp://user:pass@ip:554/stream"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              imgsz (opsional, default 640)
            </label>
            <input
              type="number"
              value={imgsz}
              onChange={(e) => setImgsz(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="960 utk kamera dgn banyak motor kecil"
            />
          </div>

          <button
            type="button"
            onClick={handleTest}
            disabled={!rtspUrl || testing}
            className="w-full border border-brand-500 text-brand-700 rounded-lg py-2 text-sm font-semibold hover:bg-brand-50 disabled:opacity-50"
          >
            {testing ? "Menguji koneksi..." : "Test Koneksi"}
          </button>

          {testResult && (
            <div
              className={`text-sm rounded-lg px-3 py-2 ${
                testResult.berhasil ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
              }`}
            >
              {testResult.berhasil ? "✓" : "✗"} {testResult.pesan}
            </div>
          )}

          {error && <div className="text-sm text-red-600">{error}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? "Menyimpan..." : "Simpan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
