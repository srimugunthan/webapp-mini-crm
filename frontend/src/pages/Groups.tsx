import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Group, Template } from "../types";
import type { components } from "../api-types";

type GroupCreate = components["schemas"]["GroupCreate"]; // generated from the backend OpenAPI schema

export default function Groups() {
  const qc = useQueryClient();
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups") });
  const templates = useQuery({ queryKey: ["templates"], queryFn: () => api.get<Template[]>("/api/pipelines") });
  const [name, setName] = useState("");
  const [tpl, setTpl] = useState<string | null>(null); // null = not touched yet -> starter preselected
  const starter = templates.data?.find((t) => t.name === "Starter")?.id;
  const chosen = tpl ?? (starter !== undefined ? String(starter) : "none");
  const csvInput = useRef<HTMLInputElement>(null);
  const [note, setNote] = useState("");
  const create = useMutation({
    mutationFn: async () => {
      const g = await api.send<Group>("POST", "/api/groups", { name, template_id: chosen === "none" ? null : Number(chosen) } satisfies GroupCreate);
      const f = csvInput.current?.files?.[0];
      if (!f) return `Created “${g.name}”.`;
      try {
        const r = await api.upload<{ added: number; not_found: number }>(`/api/groups/${g.id}/members/csv?apply=true`, f);
        return `Created “${g.name}” with ${r.added} people from the CSV${r.not_found ? ` (${r.not_found} URLs were not found in your contacts)` : ""}.`;
      } catch (e) {
        return `Created “${g.name}”, but the CSV could not be used: ${(e as Error).message} You can retry from the group page (Add members).`;
      }
    },
    onSuccess: (text) => { setName(""); setNote(text); if (csvInput.current) csvInput.current.value = ""; qc.invalidateQueries(); },
    onMutate: () => setNote(""),
  });
  const del = useMutation({ mutationFn: (id: number) => api.send("DELETE", `/api/groups/${id}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) });
  const rename = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => api.send("PATCH", `/api/groups/${id}`, { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
  return (
    <>
      <h1>Groups</h1>
      <form className="toolbar" onSubmit={(e) => { e.preventDefault(); name.trim() && create.mutate(); }}>
        <input placeholder="New group name" aria-label="Group name" value={name} onChange={(e) => setName(e.target.value)} />
        <select aria-label="Pipeline" value={chosen} onChange={(e) => setTpl(e.target.value)}>
          <option value="none">No pipeline</option>
          {templates.data?.map((t) => <option key={t.id} value={t.id}>{t.name}: {t.stages.map((s) => s.name).join(" → ")}</option>)}
        </select>
        <label className="muted">Optional: add people from a CSV (URL column){" "}
          <input ref={csvInput} type="file" accept=".csv,text/csv" aria-label="Members CSV" />
        </label>
        <button className="primary" type="submit" disabled={!name.trim() || create.isPending}>Create group</button>
      </form>
      <p className="muted">You can also add people later: open the group and use <b>Add members</b>, or tick contacts on the Contacts page.</p>
      {note && <p className="toast" role="status">{note}</p>}
      {create.error && <p className="error" role="alert">{(create.error as Error).message}</p>}
      {rename.error && <p className="error" role="alert">{(rename.error as Error).message}</p>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Members</th><th>Pipeline</th><th></th></tr></thead>
          <tbody>
            {groups.data?.map((g) => (
              <tr key={g.id}>
                <td><Link to={`/groups/${g.id}`}>{g.name}</Link></td>
                <td>{g.member_count}</td>
                <td>{g.stage_count ? `${g.stage_count} stages` : <span className="muted">none</span>}</td>
                <td>
                  <button onClick={() => { const n = window.prompt("Rename group", g.name); if (n && n.trim() && n !== g.name) rename.mutate({ id: g.id, name: n }); }}>Rename</button>{" "}
                  <button className="danger" onClick={() => { if (window.confirm(`Delete "${g.name}"? It has ${g.member_count} members. Contacts are not deleted.`)) del.mutate(g.id); }}>Delete</button>
                </td>
              </tr>
            ))}
            {groups.data?.length === 0 && <tr><td colSpan={4} className="muted">No groups yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
