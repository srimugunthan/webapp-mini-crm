import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, qs } from "../api";
import type { Group, Member, Paged, Stage, StageCounts } from "../types";
import { dateInputToEpoch, epochToDateInput, fmtShort, fmtTs, fullName, stepStage } from "../util";
import AddMembersModal from "../components/AddMembersModal";
import BulkModal from "../components/BulkModal";
import Board from "../components/Board";
import LinkedInLink from "../components/LinkedInLink";
import PipelineModal from "../components/PipelineModal";
import StageNoteModal from "../components/StageNoteModal";

const PAGE = 100;

export default function GroupPage() {
  const gid = Number(useParams().id);
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const get = (k: string) => sp.get(k) ?? "";
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (!v) n.delete(k); else n.set(k, v);
    if (k !== "page") { n.delete("page"); setSelected(new Set()); }
    setSp(n, { replace: true });
  };
  const view = get("view") === "board" ? "board" : "table";
  const stageFilter = get("stage");
  const showFinal = sp.get("final") === "1"; // final-stage members hidden by default (FR-45)
  const sort = get("sort") || "name", order = get("order") || "asc";
  const page = Number(get("page") || 0);

  const group = useQuery({ queryKey: ["group", gid], queryFn: () => api.get<Group>(`/api/groups/${gid}`) });
  const stages = useQuery({ queryKey: ["stages", gid], queryFn: () => api.get<Stage[]>(`/api/groups/${gid}/stages`) });
  const counts = useQuery({ queryKey: ["stage-counts", gid], queryFn: () => api.get<StageCounts>(`/api/groups/${gid}/stage-counts`) });
  const hasPipeline = (stages.data?.length ?? 0) > 0;
  const params = { stage: stageFilter, q: get("q"), not_visited_days: get("nv"), not_messaged_days: get("nm"), overdue: sp.has("overdue"), hide_final: hasPipeline && !showFinal && !stageFilter, sort, order, all: view === "board", offset: page * PAGE, limit: PAGE };
  const members = useQuery({ queryKey: ["members", gid, params], queryFn: () => api.get<Paged<Member>>(`/api/groups/${gid}/members${qs(params)}`), placeholderData: (p) => p });

  const [pipeline, setPipeline] = useState(false);
  const [bulk, setBulk] = useState(false);
  const [addMembers, setAddMembers] = useState(false);
  const [pending, setPending] = useState<{ m: Member; stage: Stage | null } | null>(null);
  const [msg, setMsg] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [err, setErr] = useState("");
  const refresh = () => { qc.invalidateQueries({ queryKey: ["members", gid] }); qc.invalidateQueries({ queryKey: ["stage-counts", gid] }); qc.invalidateQueries({ queryKey: ["group", gid] }); };
  const patch = useMutation({
    mutationFn: ({ cid, body }: { cid: number; body: object }) => api.send("PATCH", `/api/groups/${gid}/members/${cid}`, body),
    onSuccess: refresh, onError: (e: Error) => setErr(e.message),
  });
  const [dates, setDates] = useState<Record<number, string>>({});
  const messaged = useMutation({
    mutationFn: ({ id, date }: { id: number; date?: string }) => api.send("POST", `/api/contacts/${id}/messaged`, date ? { date } : {}),
    onSuccess: (_r, v) => { setDates((d) => { const n = { ...d }; delete n[v.id]; return n; }); refresh(); },
    onError: (e: Error) => setErr(e.message),
  });
  const remove = useMutation({ mutationFn: (cid: number) => api.send("DELETE", `/api/groups/${gid}/members/${cid}`), onSuccess: refresh });
  const bulkMessaged = useMutation({
    mutationFn: () => api.send("POST", "/api/contacts/messaged-bulk", { ids: [...selected] }),
    onSuccess: () => { setMsg(`Marked ${selected.size} as messaged.`); setSelected(new Set()); refresh(); },
  });
  const removeSelected = useMutation({
    mutationFn: () => Promise.all([...selected].map((cid) => api.send("DELETE", `/api/groups/${gid}/members/${cid}`))),
    onSuccess: () => { setMsg(`Removed ${selected.size} from the group.`); setSelected(new Set()); refresh(); },
  });
  const toggle = (id: number) => { const n = new Set(selected); n.has(id) ? n.delete(id) : n.add(id); setSelected(n); };
  const undo = useMutation({
    mutationFn: () => api.send<{ restored: number; removed: number }>("POST", `/api/groups/${gid}/bulk-stage/undo`),
    onSuccess: (r) => { setErr(""); setMsg(`Undone: ${r.restored} restored, ${r.removed} removed.`); refresh(); },
    onError: (e: Error) => { setMsg(""); setErr(e.message); },
  });

  /** Every stage move (dropdown, next/back, drag) goes through here: final-stage confirm, then optional note. */
  const requestMove = (m: Member, stage: Stage | null) => {
    setErr(""); setMsg("");
    if (stage?.is_final && !window.confirm(`Move ${fullName(m)} into the final stage “${stage.name}”?`)) return;
    setPending({ m, stage });
  };
  const stageList = stages.data ?? [];
  const items = members.data?.items ?? [];
  const total = members.data?.total ?? 0;
  const sortBy = (c: string) => { const n = new URLSearchParams(sp); n.set("sort", c); n.set("order", sort === c && order === "asc" ? "desc" : "asc"); n.delete("page"); setSp(n, { replace: true }); };
  const arrow = (c: string) => (sort === c ? (order === "asc" ? " ▲" : " ▼") : "");
  const now = Date.now() / 1000;

  if (group.isError) return <p className="error">Group not found. <Link to="/groups">Back to groups</Link></p>;

  return (
    <>
      <div className="toolbar">
        <h1 style={{ margin: 0 }}>{group.data?.name ?? "…"}</h1>
        {hasPipeline && (
          <>
            <button className={view === "table" ? "primary" : ""} onClick={() => set("view", "")}>Table</button>
            <button className={view === "board" ? "primary" : ""} onClick={() => set("view", "board")}>Board</button>
          </>
        )}
        <button className="primary" onClick={() => setAddMembers(true)}>Add members</button>
        <button onClick={() => setPipeline(true)}>{hasPipeline ? "Edit stages" : "Add pipeline"}</button>
        <button onClick={() => setBulk(true)} disabled={!hasPipeline} title={hasPipeline ? "" : "This group has no pipeline"}>Bulk set stage</button>
        <button onClick={() => undo.mutate()} disabled={!hasPipeline}>Undo last bulk change</button>
        <a href={`/api/export?group_id=${gid}`}>Export CSV</a>
      </div>
      {msg && <p className="toast" role="status">{msg}</p>}
      {view === "table" && (
        <div className="panel" data-testid="selection-bar">
          {selected.size === 0 ? (
            <div className="row"><span className="muted">Tick members to export them, mark them messaged, or remove them from the group.</span>
              <a href={`/api/export?group_id=${gid}`}>Export whole group CSV</a></div>
          ) : (
            <div className="row">
              <b>{selected.size} selected</b>
              <button className="link" onClick={() => setSelected(new Set())}>Clear selection</button>
              <a href={`/api/export?group_id=${gid}&ids=${[...selected].join(",")}`} role="button">Export {selected.size} selected CSV</a>
              <button disabled={bulkMessaged.isPending} onClick={() => bulkMessaged.mutate()}>Mark {selected.size} messaged (now)</button>
              <button className="danger" disabled={removeSelected.isPending}
                onClick={() => window.confirm(`Remove ${selected.size} people from this group? They stay in your contacts.`) && removeSelected.mutate()}>Remove {selected.size} from group</button>
            </div>
          )}
        </div>
      )}
      {err && <p className="error" role="alert">{err}</p>}

      {hasPipeline && counts.data && (
        <div className="chips" data-testid="chips">
          <button className={`chip${!stageFilter ? " active" : ""}`} onClick={() => set("stage", "")}>All {counts.data.total}</button>
          {counts.data.stages.map((s) => (
            <button key={s.stage_id} className={`chip${stageFilter === String(s.stage_id) ? " active" : ""}`} onClick={() => set("stage", String(s.stage_id))}>{s.name} {s.count}</button>
          ))}
          {counts.data.unstaged > 0 && <button className={`chip${stageFilter === "none" ? " active" : ""}`} onClick={() => set("stage", "none")}>No stage {counts.data.unstaged}</button>}
        </div>
      )}
      {!hasPipeline && <p className="muted">This group has no pipeline, so members have no stage. Use “Add pipeline” to apply a template.</p>}

      <div className="toolbar">
        <input placeholder="Search members" aria-label="Search members" value={get("q")} onChange={(e) => set("q", e.target.value)} />
        <label>not visited in <input size={3} aria-label="Not visited days" value={get("nv")} onChange={(e) => set("nv", e.target.value.replace(/\D/g, ""))} /> days</label>
        <label>not messaged in <input size={3} aria-label="Not messaged days" value={get("nm")} onChange={(e) => set("nm", e.target.value.replace(/\D/g, ""))} /> days</label>
        <label><input type="checkbox" checked={sp.has("overdue")} onChange={(e) => set("overdue", e.target.checked ? "1" : "")} /> follow-up overdue</label>
        {hasPipeline && <label><input type="checkbox" checked={showFinal} onChange={(e) => set("final", e.target.checked ? "1" : "")} /> show final-stage members</label>}
      </div>

      {view === "board" && hasPipeline ? (
        <Board stages={stageList} members={items} onMove={(m, id) => requestMove(m, stageList.find((s) => s.id === id) ?? null)} />
      ) : (
        <>
          <div className="table-wrap">
            <table className="contacts">
              <thead><tr>
                <th><input type="checkbox" aria-label="Select all on page" checked={items.length > 0 && items.every((m) => selected.has(m.contact_id))} onChange={(e) => setSelected(e.target.checked ? new Set(items.map((m) => m.contact_id)) : new Set())} /></th>
                <th className="sortable" onClick={() => sortBy("name")}>Name{arrow("name")}</th><th>Title</th><th className="sortable" onClick={() => sortBy("company")}>Company{arrow("company")}</th><th>LinkedIn</th>
                <th className="sortable" onClick={() => sortBy("last_visited_at")}>Visited{arrow("last_visited_at")}</th><th className="sortable" onClick={() => sortBy("last_messaged_at")}>Messaged{arrow("last_messaged_at")}</th>
                {hasPipeline && <><th className="sortable" onClick={() => sortBy("stage")}>Stage{arrow("stage")}</th><th className="sortable" onClick={() => sortBy("days_in_stage")}>In stage{arrow("days_in_stage")}</th></>}
                <th className="sortable" onClick={() => sortBy("next_follow_up_at")}>Follow-up{arrow("next_follow_up_at")}</th><th>Log message</th><th></th>
              </tr></thead>
              <tbody>
                {items.map((m) => {
                  const overdue = m.next_follow_up_at !== null && m.next_follow_up_at < now;
                  return (
                    <tr key={m.contact_id} className={`${overdue ? "overdue" : ""} ${selected.has(m.contact_id) ? "selected" : ""}`} data-testid={`row-${m.contact_id}`}>
                      <td><input type="checkbox" aria-label={`Select ${fullName(m)}`} checked={selected.has(m.contact_id)} onChange={() => toggle(m.contact_id)} /></td>
                      <td>{fullName(m)}</td><td className="wrap">{m.position}</td><td className="wrap">{m.company}</td>
                      <td><LinkedInLink id={m.contact_id} url={m.linkedin_url} /></td>
                      <td title={fmtTs(m.last_visited_at)}>{fmtShort(m.last_visited_at)}</td><td title={fmtTs(m.last_messaged_at)}>{fmtShort(m.last_messaged_at)}</td>
                      {hasPipeline && (<>
                        <td><select aria-label={`Stage for ${fullName(m)}`} value={m.stage_id ?? ""} onChange={(e) => requestMove(m, stageList.find((s) => s.id === Number(e.target.value)) ?? null)}>
                          <option value="">No stage</option>{stageList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select></td>
                        <td>{m.days_in_stage === null ? "—" : `${m.days_in_stage}d`}{" "}
                          <button aria-label={`Previous stage for ${fullName(m)}`} disabled={!stepStage(stageList, m.stage_id, -1)} onClick={() => requestMove(m, stepStage(stageList, m.stage_id, -1))}>&lt;</button>
                          <button aria-label={`Next stage for ${fullName(m)}`} disabled={!stepStage(stageList, m.stage_id, 1)} onClick={() => requestMove(m, stepStage(stageList, m.stage_id, 1))}>&gt;</button></td>
                      </>)}
                      <td><input type="date" aria-label={`Follow-up for ${fullName(m)}`} defaultValue={epochToDateInput(m.next_follow_up_at)} key={`${m.contact_id}-${m.next_follow_up_at}`}
                        onChange={(e) => patch.mutate({ cid: m.contact_id, body: { next_follow_up_at: dateInputToEpoch(e.target.value) } })} /></td>
                      <td className="actions">
                        <button onClick={() => messaged.mutate({ id: m.contact_id })}>Mark messaged</button>{" "}
                        <input type="date" aria-label={`Messaged date for ${fullName(m)}`} value={dates[m.contact_id] ?? ""} onChange={(e) => setDates({ ...dates, [m.contact_id]: e.target.value })} />
                        <button disabled={!dates[m.contact_id]} onClick={() => messaged.mutate({ id: m.contact_id, date: dates[m.contact_id] })}>Set</button>
                      </td>
                      <td><button className="danger" title="Remove from group" aria-label={`Remove ${fullName(m)} from group`} onClick={() => window.confirm(`Remove ${fullName(m)} from this group?`) && remove.mutate(m.contact_id)}>✕</button></td>
                    </tr>
                  );
                })}
                {items.length === 0 && <tr><td colSpan={13} className="muted">No members match.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="toolbar" style={{ marginTop: 10 }}>
            <button disabled={page === 0} onClick={() => set("page", String(page - 1))}>← Prev</button>
            <span>Page {page + 1} of {Math.max(1, Math.ceil(total / PAGE))} ({total} members)</span>
            <button disabled={(page + 1) * PAGE >= total} onClick={() => set("page", String(page + 1))}>Next →</button>
          </div>
        </>
      )}

      {pending && (
        <StageNoteModal label={`Move ${fullName(pending.m)} to ${pending.stage?.name ?? "No stage"}`} onCancel={() => setPending(null)}
          onDone={(note) => { patch.mutate({ cid: pending.m.contact_id, body: { stage_id: pending.stage?.id ?? null, note } }); setPending(null); }} />
      )}
      {pipeline && <PipelineModal groupId={gid} groupName={group.data?.name ?? ""} onClose={() => setPipeline(false)} />}
      {addMembers && <AddMembersModal groupId={gid} groupName={group.data?.name ?? ""} onClose={() => setAddMembers(false)} />}
      {bulk && <BulkModal groupId={gid} stages={stageList} onClose={() => setBulk(false)} />}
    </>
  );
}
