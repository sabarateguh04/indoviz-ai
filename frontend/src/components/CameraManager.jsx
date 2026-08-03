import { useState } from "react";
import { deleteCamera } from "../services/api.js";
import AddCameraModal from "./AddCameraModal.jsx";
import ZoneEditor from "./ZoneEditor.jsx";

const STATUS_DOT = { online: "bg-emerald-400", warning: "bg-amber-400", offline: "bg-red-400" };

export default function CameraManager({ cameras, onClose, onChanged }) {
  const [editing, setEditing] = useState(null); // null = tertutup, {} = tambah baru, {id,...} = edit
  const [zoningCamera, setZoningCamera] = useState(null);
  const [error, setError] = useState(null);

  async function handleDelete(camera) {
    if (!window.confirm(`Hapus kamera "${camera.nama}"?`)) return;
    try {
      await deleteCamera(camera.id);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleSaved() {
    setEditing(null);
    onChanged();
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-5 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-800">Kelola Kamera</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <button
          onClick={() => setEditing({})}
          className="mb-4 px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700"
        >
          + Tambah Kamera
        </button>

        {error && <div className="text-sm text-red-600 mb-2">{error}</div>}

        <ul className="space-y-2">
          {cameras.length === 0 && <li className="text-sm text-slate-400">Belum ada kamera</li>}
          {cameras.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between border border-slate-200 rounded-lg px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_DOT[c.status] || "bg-slate-300"}`} />
                <div className="min-w-0">
                  <div className="font-medium text-slate-800 truncate">{c.nama}</div>
                  <div className="text-xs text-slate-400 font-mono truncate">{c.rtsp_url}</div>
                </div>
              </div>
              <div className="flex gap-3 text-sm shrink-0 ml-2">
                <button onClick={() => setZoningCamera(c)} className="text-brand-600 hover:underline">
                  Atur Zona
                </button>
                <button onClick={() => setEditing(c)} className="text-slate-600 hover:underline">
                  Edit
                </button>
                <button onClick={() => handleDelete(c)} className="text-red-600 hover:underline">
                  Hapus
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {editing && (
        <AddCameraModal camera={editing.id ? editing : null} onClose={() => setEditing(null)} onSaved={handleSaved} />
      )}

      {zoningCamera && <ZoneEditor camera={zoningCamera} onClose={() => setZoningCamera(null)} />}
    </div>
  );
}
