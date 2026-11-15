import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { ApplyPlan, Stage, Template } from "../types";
import Modal from "./Modal";

/** Stage editor + save-as-template + apply/remove pipeline for one group. */
export default function PipelineModal({ groupId, groupName, onClose }: { groupId: number; groupName: string; onClose: () => void }) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries();
  const stages = useQuery({ queryKey: ["stages", groupId], queryFn: () => api.get<Stage[]>(`/api/groups/${groupId}/stages`) });
  const templates = useQuery({ queryKey: ["templates"], queryFn: () => api.get<Template[]>("/api/pipelines") });
  const [newName, setNewName] = useState("");
  const [paste, setPaste] = useState("");
  const [tplName, setTplName] = useState("");
  const [applyId, setApplyId] = useState("");
  const [plan, setPlan] = useState<ApplyPlan | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [deleting, setDeleting] = useState<{ stage: Stage; count: number } | null>(null);
  const [moveTo, setMoveTo] = useState("");
  const [note, setNote] = useState("");

  const wrap = <A,>(fn: (a: A) => Promise<unknown>) => useMutation({ mutationFn: fn, onSuccess: () => { setNote(""); refresh(); }, onError: (e: Error) => setNote(e.message) });
  const add = wrap(() => api.send("POST", `/api/groups/${groupId}/stages`, { name: newName }).then(() => setNewName("")));
  const addList = wrap(() => api.send("POST", `/api/groups/${groupId}/stages`, { names: paste.split(",") }).then(() => setPaste("")));
  const patch = wrap(({ id, body }: { id: number; body: object }) => api.send("PATCH", `/api/stages/${id}`, body));
  const saveTpl = wrap(() => api.send("POST", "/api/pipelines", { name: tplName, from_group_id: groupId }).then(() => { setTplName(""); setNote("Saved as template."); }));
  const remove = wrap(() => api.send("DELETE", `/api/groups/${groupId}/pipeline?confirm=true`));

  const tryDelete = async (s: Stage) => {
    try { await api.send("DELETE", `/api/stages/${s.id}`); refresh(); setNote(""); }
    catch (e: any) {
      if (e.status === 409) setDeleting({ stage: s, count: e.detail.member_count }); else setNote(e.message);
    }
  };
  const confirmDelete = async () => {
    if (!deleting) return;
    const q = moveTo === "clear" ? "clear=true" : `move_to=${moveTo}`;
    try { await api.send("DELETE", `/api/stages/${deleting.stage.id}?${q}`); setDeleting(null); setMoveTo(""); refresh(); }
    catch (e: any) { setNote(e.message); }
  };
  const doPreview = async (m = mapping) => {
    try { setPlan(await api.send<ApplyPlan>("POST", `/api/groups/${groupId}/pipeline`, { template_id: Number(applyId), preview: true, mapping: m })); setNote(""); }
    catch (e: any) { setNote(e.message); }
  };
  const doApply = async () => {
    try { await api.send("POST", `/api/groups/${groupId}/pipeline`, { template_id: Number(applyId), preview: false, mapping }); setPlan(null); setApplyId(""); setMapping({}); refresh(); setNote("Pipeline applied."); }
    catch (e: any) { setNote(e.message); }
  };
  const list = stages.data ?? [];
  const unmatchedOk = plan ? plan.unmatched.every((u) => mapping[String(u.stage_id)]) : false;

  return (
    <Modal title={`Pipeline: ${groupName}`} onClose={onClose} wide>
      {note && <p className={note.startsWith("Saved") || note.startsWith("Pipeline applied") ? "toast" : "error"} role="status">{note}</p>}
      <h2>Stages</h2>
      {list.length === 0 && <p className="muted">This group has no pipeline. Add stages below or apply a template.</p>}
      {list.map((s, i) => (
        <div className="row" key={s.id}>
          <input defaultValue={s.name} aria-label={`Stage ${s.name} name`} onBlur={(e) => e.target.value.trim() && e.target.value !== s.name && patch.mutate({ id: s.id, body: { name: e.target.value } })} />
          <label><input type="checkbox" checked={s.is_final} onChange={(e) => patch.mutate({ id: s.id, body: { is_final: e.target.checked } })} /> final</label>
          <button disabled={i === 0} aria-label={`Move ${s.name} up`} onClick={() => patch.mutate({ id: s.id, body: { position: i - 1 } })}>↑</button>
          <button disabled={i === list.length - 1} aria-label={`Move ${s.name} down`} onClick={() => patch.mutate({ id: s.id, body: { position: i + 1 } })}>↓</button>
          <button className="danger" onClick={() => tryDelete(s)}>Delete</button>
        </div>
      ))}
      {deleting && (
        <div className="panel">
          <p><b>{deleting.stage.name}</b> has {deleting.count} members. Move them to:</p>
          <div className="row">
            <select aria-label="Move members to" value={moveTo} onChange={(e) => setMoveTo(e.target.value)}>
              <option value="">Choose…</option>
              {list.filter((s) => s.id !== deleting.stage.id).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              <option value="clear">— clear their stage —</option>
            </select>
            <button className="danger" disabled={!moveTo} onClick={confirmDelete}>Delete stage</button>
            <button onClick={() => setDeleting(null)}>Cancel</button>
          </div>
        </div>
      )}
      <div className="row">
        <input placeholder="New stage" aria-label="New stage name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button disabled={!newName.trim()} onClick={() => add.mutate(undefined)}>Add stage</button>
      </div>
      <div className="row">
        <input style={{ flex: 1 }} placeholder="Paste comma-separated list to append stages" aria-label="Pasted stage list" value={paste} onChange={(e) => setPaste(e.target.value)} />
        <button disabled={!paste.trim()} onClick={() => addList.mutate(undefined)}>Add list</button>
      </div>

      <h2>Apply a template</h2>
      <div className="row">
        <select aria-label="Template to apply" value={applyId} onChange={(e) => { setApplyId(e.target.value); setPlan(null); setMapping({}); }}>
          <option value="">Choose template…</option>
          {templates.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <button disabled={!applyId} onClick={() => doPreview()}>Preview</button>
      </div>
      {plan && (
        <div className="panel" data-testid="apply-preview">
          <p>New stages: {plan.template_stages.join(" → ")}</p>
          <p>{plan.no_stage_to_first} members without a stage will move to <b>{plan.first_stage}</b>.</p>
          {plan.mapped.map((m) => <p key={m.stage_id}>{m.count} in “{m.stage_name}” → “{m.to}”</p>)}
          {plan.unmatched.map((u) => (
            <div className="row" key={u.stage_id}>
              <span>{u.count} in “{u.stage_name}” → </span>
              <select aria-label={`Map ${u.stage_name}`} value={mapping[String(u.stage_id)] ?? ""} onChange={(e) => setMapping({ ...mapping, [String(u.stage_id)]: e.target.value })}>
                <option value="">Choose stage…</option>
                {plan.template_stages.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          ))}
          <button className="primary" disabled={!unmatchedOk} onClick={doApply}>Confirm and apply</button>
        </div>
      )}

      <h2>Save as template</h2>
      <div className="row">
        <input placeholder="Template name" aria-label="Save template name" value={tplName} onChange={(e) => setTplName(e.target.value)} />
        <button disabled={!tplName.trim() || list.length === 0} onClick={() => saveTpl.mutate(undefined)}>Save group's stages as template</button>
      </div>

      {list.length > 0 && (<>
        <h2>Remove pipeline</h2>
        <button className="danger" onClick={() => window.confirm("Remove this pipeline? Members will lose their stage (stage history is kept).") && remove.mutate(undefined)}>Remove pipeline…</button>
      </>)}
    </Modal>
  );
}
