import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, qs } from "../api";
import type { Contact, Paged } from "../types";
import { fullName } from "../util";
import Modal from "./Modal";

interface CsvResult {
  to_add: number; already_members: number; not_found: number; applied: boolean; added: number;
  problems: { row: number; url: string; reason: string }[];
}

/** Add people to a group: search and tick them, or upload a CSV with a URL column. */
export default function AddMembersModal({ groupId, groupName, onClose }: { groupId: number; groupName: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"search" | "csv">("search");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const [pv, setPv] = useState<CsvResult | null>(null);

  const results = useQuery({
    queryKey: ["contacts", "picker", q],
    queryFn: () => api.get<Paged<Contact>>(`/api/contacts${qs({ q, limit: 50 })}`),
    placeholderData: (p) => p,
  });
  const refresh = () => qc.invalidateQueries();
  const run = async (fn: () => Promise<void>) => { try { setMsg(null); await fn(); } catch (e: any) { setMsg({ kind: "err", text: e.message }); } };

  const addSelected = () => run(async () => {
    const r = await api.send<{ added: number; already_members: number }>("POST", `/api/groups/${groupId}/members`, { contact_ids: [...sel] });
    setSel(new Set()); refresh();
    setMsg({ kind: "ok", text: `Added ${r.added}${r.already_members ? `, ${r.already_members} were already in the group` : ""}.` });
  });
  const csv = (apply: boolean) => run(async () => {
    const f = file.current?.files?.[0];
    if (!f) return setMsg({ kind: "err", text: "Choose a CSV file first." });
    const r = await api.upload<CsvResult>(`/api/groups/${groupId}/members/csv${qs({ apply })}`, f);
    setPv(r);
    if (apply) { refresh(); setMsg({ kind: "ok", text: `Added ${r.added} people to ${groupName}.` }); }
  });
  const toggle = (id: number) => { const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n); };
  const items = results.data?.items ?? [];

  return (
    <Modal title={`Add people to ${groupName}`} onClose={onClose} wide>
      <div className="row">
        <button className={tab === "search" ? "primary" : ""} onClick={() => setTab("search")}>Pick from contacts</button>
        <button className={tab === "csv" ? "primary" : ""} onClick={() => setTab("csv")}>Upload CSV</button>
      </div>
      {msg && <p className={msg.kind === "ok" ? "toast" : "error"} role="status">{msg.text}</p>}

      {tab === "search" ? (
        <>
          <div className="row">
            <input style={{ flex: 1 }} placeholder="Search name, company or position" aria-label="Search contacts to add" value={q} onChange={(e) => setQ(e.target.value)} />
            <button className="primary" disabled={!sel.size} onClick={addSelected}>Add {sel.size || ""} selected</button>
          </div>
          <div className="table-wrap" style={{ maxHeight: 340, overflow: "auto" }}>
            <table>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id}>
                    <td><input type="checkbox" aria-label={`Add ${fullName(c)}`} checked={sel.has(c.id)} onChange={() => toggle(c.id)} /></td>
                    <td>{fullName(c)}</td><td>{c.position}</td><td>{c.company}</td>
                    <td>{c.groups.some((g) => g.id === groupId) && <span className="badge">already in group</span>}</td>
                  </tr>
                ))}
                {items.length === 0 && <tr><td className="muted">No contacts match.</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="muted">Showing up to 50 matches. Tip: on the Contacts page you can filter and add hundreds at once.</p>
        </>
      ) : (
        <>
          <p className="muted">Upload a CSV with a <b>URL</b> column (your LinkedIn connections export works as is). People are matched to your
            existing contacts by LinkedIn URL; nobody new is created. Anyone not found is listed.</p>
          <div className="row">
            <input ref={file} type="file" accept=".csv,text/csv" aria-label="Members CSV" onChange={() => setPv(null)} />
            <button onClick={() => csv(false)}>Preview</button>
          </div>
          {pv && (
            <div className="panel" data-testid="members-csv-preview">
              <p>{pv.applied ? "Result" : "Preview"}: <b>{pv.applied ? pv.added : pv.to_add}</b> {pv.applied ? "added" : "will be added"} · {pv.already_members} already in the group · {pv.not_found} URLs not found</p>
              {pv.problems.length > 0 && <ul>{pv.problems.slice(0, 10).map((p) => <li key={p.row}>Row {p.row}: {p.url || "(empty)"} — {p.reason}</li>)}{pv.problems.length > 10 && <li>…and {pv.problems.length - 10} more</li>}</ul>}
              {!pv.applied && <button className="primary" disabled={pv.to_add === 0} onClick={() => csv(true)}>Add {pv.to_add} people</button>}
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
