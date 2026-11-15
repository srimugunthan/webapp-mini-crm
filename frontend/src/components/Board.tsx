import { useState } from "react";
import type { Member, Stage } from "../types";
import { fullName } from "../util";

/** Board view: one column per stage; native HTML5 drag-and-drop with a dropdown alternative on every card. */
export default function Board({ stages, members, onMove }: { stages: Stage[]; members: Member[]; onMove: (m: Member, stageId: number | null) => void }) {
  const [over, setOver] = useState<number | "none" | null>(null);
  const cols: { id: number | null; name: string }[] = [...(members.some((m) => m.stage_id === null) ? [{ id: null, name: "No stage" }] : []), ...stages.map((s) => ({ id: s.id, name: s.name }))];
  return (
    <div className="board" data-testid="board">
      {cols.map((col) => {
        const key = col.id ?? "none";
        return (
          <div key={key} className={`col${over === key ? " over" : ""}`} data-testid={`col-${col.name}`}
            onDragOver={(e) => { e.preventDefault(); setOver(key); }} onDragLeave={() => setOver(null)}
            onDrop={(e) => {
              e.preventDefault(); setOver(null);
              const m = members.find((x) => x.contact_id === Number(e.dataTransfer.getData("text/plain")));
              if (m && m.stage_id !== col.id) onMove(m, col.id);
            }}>
            <h3>{col.name} <span className="muted">{members.filter((m) => m.stage_id === col.id).length}</span></h3>
            {members.filter((m) => m.stage_id === col.id).map((m) => (
              <div className="card" key={m.contact_id} draggable data-testid={`card-${m.contact_id}`}
                onDragStart={(e) => e.dataTransfer.setData("text/plain", String(m.contact_id))}>
                <b>{fullName(m)}</b><br /><span className="muted">{m.position}{m.company ? `, ${m.company}` : ""}</span><br />
                <span className="muted">{m.days_in_stage ?? "–"}d</span>{" "}
                <select aria-label={`Stage for ${fullName(m)}`} value={m.stage_id ?? ""} onChange={(e) => onMove(m, e.target.value ? Number(e.target.value) : null)}>
                  <option value="">No stage</option>
                  {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
