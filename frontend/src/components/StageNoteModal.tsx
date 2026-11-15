import { useEffect, useRef, useState } from "react";

/** Optional one-line note on a stage move. Enter saves, Esc skips the note (one keystroke). */
export default function StageNoteModal({ label, onDone, onCancel }: { label: string; onDone: (note: string | undefined) => void; onCancel: () => void }) {
  const [note, setNote] = useState("");
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div className="overlay" role="dialog" aria-label="Stage move note">
      <div className="modal">
        <h1>{label}</h1>
        <input ref={ref} style={{ width: "100%" }} value={note} placeholder="Optional note — Enter to save, Esc to skip" aria-label="Stage note"
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onDone(note.trim() || undefined);
            if (e.key === "Escape") { e.stopPropagation(); onDone(undefined); }
          }} />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="primary" onClick={() => onDone(note.trim() || undefined)}>Move</button>
          <button onClick={() => onDone(undefined)}>Move without note</button>
          <button onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
