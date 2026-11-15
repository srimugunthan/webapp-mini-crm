import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { BulkPreview, Stage } from "../types";
import Modal from "./Modal";

export default function BulkModal({ groupId, stages, onClose }: { groupId: number; stages: Stage[]; onClose: () => void }) {
  const qc = useQueryClient();
  const file = useRef<HTMLInputElement>(null);
  const [stage, setStage] = useState(stages[0] ? String(stages[0].id) : "");
  const [pv, setPv] = useState<BulkPreview | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const run = async (fn: () => Promise<void>) => { try { setMsg(null); await fn(); } catch (e: any) { setMsg({ kind: "err", text: e.message }); } };
  const preview = () => run(async () => {
    const f = file.current?.files?.[0];
    if (!f) return setMsg({ kind: "err", text: "Choose a CSV file first." });
    setPv(await api.upload<BulkPreview>(`/api/groups/${groupId}/bulk-stage?preview=true`, f, stage ? { stage_id: stage } : {}));
  });
  const apply = () => run(async () => {
    const r = await api.send<{ moved: number; added: number; unchanged: number }>("POST", `/api/groups/${groupId}/bulk-stage`, { token: pv!.token });
    setPv(null);
    qc.invalidateQueries();
    setMsg({ kind: "ok", text: `Done: ${r.moved} moved, ${r.added} added, ${r.unchanged} unchanged.` });
  });
  const c = pv?.counts;
  const stageName = stages.find((s) => String(s.id) === stage)?.name ?? "(per-row Stage column)";
  return (
    <Modal title="Bulk set stage" onClose={onClose}>
      <p className="muted">Upload a CSV with a URL column (a LinkedIn export works). An optional Stage column overrides the dropdown.</p>
      <div className="row">
        <input ref={file} type="file" accept=".csv,text/csv" aria-label="Bulk CSV" onChange={() => setPv(null)} />
        <select aria-label="Stage" value={stage} onChange={(e) => { setStage(e.target.value); setPv(null); }}>
          <option value="">(use Stage column only)</option>
          {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button onClick={preview}>Preview</button>
      </div>
      {msg && <p className={msg.kind === "ok" ? "toast" : "error"} role="status">{msg.text}</p>}
      {pv && c && (
        <div className="panel" data-testid="bulk-preview">
          <h2>Bulk set stage: {stageName}</h2>
          <p>{c.move} will be moved<br />{c.no_change} already at target stage (no change)<br />{c.add} not in this group yet (will be added)<br />
            {c.not_found} URLs not found in your contacts (skipped)<br />{c.unknown_stage} rows with unknown stage (skipped)</p>
          {pv.problems.length > 0 && <a href={`/api/groups/${groupId}/bulk-stage/${pv.token}/problems.csv`}>Download problem rows</a>}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="primary" onClick={apply} disabled={c.move + c.add === 0}>Apply</button>
            <button onClick={() => setPv(null)}>Cancel</button>
          </div>
        </div>
      )}
    </Modal>
  );
}
