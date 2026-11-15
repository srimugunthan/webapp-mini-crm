import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Template } from "../types";

export default function Pipelines() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["templates"], queryFn: () => api.get<Template[]>("/api/pipelines") });
  const [name, setName] = useState("");
  const [stages, setStages] = useState("");
  const [finalLast, setFinalLast] = useState(true);
  const refresh = () => qc.invalidateQueries({ queryKey: ["templates"] });
  const create = useMutation({
    mutationFn: () => {
      const list = stages.split(",").map((s) => s.trim()).filter(Boolean);
      return api.send("POST", "/api/pipelines", { name, stages: list.map((s, i) => ({ name: s, is_final: finalLast && i === list.length - 1 })) });
    },
    onSuccess: () => { setName(""); setStages(""); refresh(); },
  });
  const rename = useMutation({ mutationFn: ({ id, name }: { id: number; name: string }) => api.send("PATCH", `/api/pipelines/${id}`, { name }), onSuccess: refresh });
  const del = useMutation({ mutationFn: (id: number) => api.send("DELETE", `/api/pipelines/${id}`), onSuccess: refresh });
  const err = (create.error ?? rename.error ?? del.error) as Error | null;
  return (
    <>
      <h1>Pipeline templates</h1>
      <p className="muted">A template is copied into a group when applied; later edits to either side don't affect the other.
        To save a group's own stages as a template, use <i>Pipeline</i> on the group page.</p>
      <form className="panel" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <h2>New template</h2>
        <div className="row">
          <input placeholder="Template name" aria-label="Template name" value={name} onChange={(e) => setName(e.target.value)} />
          <input style={{ flex: 1, minWidth: 220 }} placeholder="Comma-separated stages: Shortlisted, Reached out, Closed" aria-label="Template stages" value={stages} onChange={(e) => setStages(e.target.value)} />
          <label><input type="checkbox" checked={finalLast} onChange={(e) => setFinalLast(e.target.checked)} /> last stage is final</label>
          <button className="primary" disabled={!name.trim() || !stages.trim()}>Create</button>
        </div>
      </form>
      {err && <p className="error" role="alert">{err.message}</p>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Stages</th><th></th></tr></thead>
          <tbody>
            {data?.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{t.stages.map((s) => s.name + (s.is_final ? " (final)" : "")).join(" → ")}</td>
                <td>
                  <button onClick={() => { const n = window.prompt("Rename template", t.name); if (n && n.trim()) rename.mutate({ id: t.id, name: n }); }}>Rename</button>{" "}
                  <button className="danger" onClick={() => window.confirm(`Delete template "${t.name}"? Groups that used it are not affected.`) && del.mutate(t.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
