import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { ContactDetail } from "../types";
import { fmtTs, fullName } from "../util";
import LinkedInLink from "./LinkedInLink";

export default function ContactDrawer({ id, onClose }: { id: number; onClose: () => void }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["contact", id], queryFn: () => api.get<ContactDetail>(`/api/contacts/${id}`) });
  const [body, setBody] = useState("");
  const add = useMutation({
    mutationFn: () => api.send("POST", `/api/contacts/${id}/notes`, { body }),
    onSuccess: () => { setBody(""); qc.invalidateQueries({ queryKey: ["contact", id] }); },
  });
  if (!data) return <aside className="drawer">Loading…</aside>;
  return (
    <aside className="drawer" aria-label="Contact detail">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{fullName(data)}</h1>
        <button onClick={onClose} aria-label="Close drawer">✕</button>
      </div>
      <p>{data.position} {data.company && `· ${data.company}`}<br />
        <LinkedInLink id={data.id} url={data.linkedin_url} /><br />
        <span className="muted">{data.email || "no email"} · connected {data.connected_on ?? "—"}</span></p>
      <p>Last visited: {fmtTs(data.last_visited_at)} · Last messaged: {fmtTs(data.last_messaged_at)}</p>
      <h2>Groups</h2>
      {data.memberships.length === 0 && <p className="muted">Not in any group.</p>}
      <ul>{data.memberships.map((m) => <li key={m.group_id}>{m.group_name}{m.stage_name ? ` — ${m.stage_name}` : ""}</li>)}</ul>
      <h2>Notes</h2>
      <div className="row">
        <input style={{ flex: 1 }} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a note" aria-label="New note"
          onKeyDown={(e) => e.key === "Enter" && body.trim() && add.mutate()} />
        <button disabled={!body.trim()} onClick={() => add.mutate()}>Add</button>
      </div>
      <ul>{data.notes.map((n) => <li key={n.id}>{n.body} <span className="muted">({fmtTs(n.created_at)})</span></li>)}</ul>
      <h2>Stage history</h2>
      {data.history.length === 0 && <p className="muted">No stage changes yet.</p>}
      <ul>{data.history.map((h) => (
        <li key={h.id}>{h.group_name}: {h.from_stage_name ?? "no stage"} → {h.to_stage_name ?? "no stage"}{" "}
          <span className="muted">({fmtTs(h.changed_at)}{h.source === "bulk" ? ", bulk" : ""}{h.note ? `, ${h.note}` : ""})</span></li>
      ))}</ul>
    </aside>
  );
}
