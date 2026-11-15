import { useState } from "react";
import Modal from "./Modal";

/** Record that you messaged someone on LinkedIn: today, or an earlier date. */
export default function LogMessageModal({ name, onSave, onClose }: { name: string; onSave: (date?: string) => void; onClose: () => void }) {
  const today = new Date();
  const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const [date, setDate] = useState(iso);
  return (
    <Modal title={`Log message to ${name}`} onClose={onClose}>
      <p className="muted">Sets “Last messaged”. Pick the day you sent it (default today).</p>
      <div className="row">
        <input type="date" aria-label="Date messaged" value={date} max={iso} onChange={(e) => setDate(e.target.value)} />
        <button className="primary" disabled={!date} onClick={() => onSave(date === iso ? undefined : date)}>Save</button>
        <button onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
