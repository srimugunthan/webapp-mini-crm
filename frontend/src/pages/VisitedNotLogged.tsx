import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Contact } from "../types";
import { fmtTs, fullName } from "../util";
import LinkedInLink from "../components/LinkedInLink";

export default function VisitedNotLogged() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["pending", "list"], queryFn: () => api.get<Contact[]>("/api/visits/pending") });
  const [sel, setSel] = useState<Set<number>>(new Set());
  const mark = useMutation({
    mutationFn: (ids: number[]) => api.send("POST", "/api/contacts/messaged-bulk", { ids }),
    onSuccess: () => { setSel(new Set()); qc.invalidateQueries(); },
  });
  const toggle = (id: number) => { const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n); };
  return (
    <>
      <h1>Visited, not logged <span className="muted">({data.length})</span></h1>
      <p className="muted">People whose profile you opened but haven't marked as messaged.</p>
      <div className="toolbar">
        <button disabled={!sel.size} className="primary" onClick={() => mark.mutate([...sel])}>Mark {sel.size} messaged (now)</button>
        <button disabled={!data.length} onClick={() => mark.mutate(data.map((c) => c.id))}>Mark all messaged</button>
        <button disabled={!data.length} onClick={() => setSel(new Set(data.map((c) => c.id)))}>Select all</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th></th><th>Name</th><th>Company</th><th>Last visited</th><th>LinkedIn</th></tr></thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.id}>
                <td><input type="checkbox" aria-label={`Select ${fullName(c)}`} checked={sel.has(c.id)} onChange={() => toggle(c.id)} /></td>
                <td>{fullName(c)}</td><td>{c.company}</td><td>{fmtTs(c.last_visited_at)}</td>
                <td><LinkedInLink id={c.id} url={c.linkedin_url} /></td>
              </tr>
            ))}
            {data.length === 0 && <tr><td colSpan={5} className="muted">Nothing to log.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
