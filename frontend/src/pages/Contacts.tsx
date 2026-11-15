import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, qs } from "../api";
import type { Contact, Group, Paged } from "../types";
import { dateInputToEpoch, fmtShort, fmtTs, fullName } from "../util";
import ContactDrawer from "../components/ContactDrawer";
import LinkedInLink from "../components/LinkedInLink";

const PAGE = 100;
const label = (k: string) => ({ name: "Name", position: "Position", company: "Company", connected_on: "Connected", last_visited_at: "Last visited", last_messaged_at: "Last messaged" } as Record<string, string>)[k];

export default function Contacts() {
  const [sp, setSp] = useSearchParams();
  const qc = useQueryClient();
  const get = (k: string) => sp.get(k) ?? "";
  const set = (k: string, v: string | boolean) => {
    const n = new URLSearchParams(sp);
    if (v === "" || v === false) n.delete(k); else n.set(k, String(v));
    if (k !== "page") n.delete("page");
    if (k !== "page") { setSelected(new Set()); setAllMatching(false); }
    setSp(n, { replace: true });
  };
  const page = Number(get("page") || 0);
  const sort = get("sort") || "name", order = get("order") || "asc";
  const params = { q: get("q"), company: get("company"), position: get("position"), group: get("group"), year: get("year"), never_visited: sp.has("never_visited"), never_messaged: sp.has("never_messaged"), no_group: sp.has("no_group"), sort, order, offset: page * PAGE, limit: PAGE };
  const { data, isLoading, error } = useQuery({ queryKey: ["contacts", params], queryFn: () => api.get<Paged<Contact>>(`/api/contacts${qs(params)}`), placeholderData: (p) => p });
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups") });
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [target, setTarget] = useState("");
  const [drawer, setDrawer] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [allMatching, setAllMatching] = useState(false);
  const [help, setHelp] = useState(false);
  const filterParams = { q: get("q"), company: get("company"), position: get("position"), group: get("group"), year: get("year"), never_visited: sp.has("never_visited"), never_messaged: sp.has("never_messaged"), no_group: sp.has("no_group") };
  const hasFilters = Object.values(filterParams).some(Boolean);
  const clearSelection = () => { setSelected(new Set()); setAllMatching(false); };
  const selectAllMatching = async () => {
    const r = await api.get<{ ids: number[]; total: number }>(`/api/contacts/ids${qs(filterParams)}`);
    setSelected(new Set(r.ids)); setAllMatching(true);
  };
  const [dates, setDates] = useState<Record<number, string>>({});

  const addToGroup = useMutation({
    mutationFn: () => api.send<{ added: number; already_members: number }>("POST", `/api/groups/${target}/members`, { contact_ids: [...selected] }),
    onSuccess: (r) => { setMsg(`Added ${r.added}, ${r.already_members} already in the group.`); clearSelection(); qc.invalidateQueries(); },
  });
  const bulkMessaged = useMutation({
    mutationFn: () => api.send("POST", "/api/contacts/messaged-bulk", { ids: [...selected] }),
    onSuccess: () => { setMsg(`Marked ${selected.size} as messaged.`); clearSelection(); qc.invalidateQueries(); },
  });
  const messaged = useMutation({
    mutationFn: ({ id, date }: { id: number; date?: string }) => api.send("POST", `/api/contacts/${id}/messaged`, date ? { date } : {}),
    onSuccess: () => qc.invalidateQueries(),
  });
  const toggle = (id: number) => { setAllMatching(false); const n = new Set(selected); n.has(id) ? n.delete(id) : n.add(id); setSelected(n); };
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const sortBy = (c: string) => { const n = new URLSearchParams(sp); n.set("sort", c); n.set("order", sort === c && order === "asc" ? "desc" : "asc"); n.delete("page"); setSp(n, { replace: true }); };

  return (
    <>
      <h1>Contacts <span className="muted">({total})</span></h1>
      <div className="toolbar">
        <input placeholder='Search: data AND (google OR acme)' aria-label="Search" size={26} value={get("q")} onChange={(e) => set("q", e.target.value)} />
        <input placeholder="Company" aria-label="Company filter" value={get("company")} onChange={(e) => set("company", e.target.value)} size={12} />
        <input placeholder="Position keyword" aria-label="Position filter" value={get("position")} onChange={(e) => set("position", e.target.value)} size={14} />
        <input placeholder="Group: HR OR ML" aria-label="Group filter" value={get("group")} onChange={(e) => set("group", e.target.value)} size={16} />
        <input placeholder="Year" aria-label="Connected year" value={get("year")} onChange={(e) => set("year", e.target.value.replace(/\D/g, "").slice(0, 4))} size={5} />
        <label><input type="checkbox" checked={sp.has("never_visited")} onChange={(e) => set("never_visited", e.target.checked)} /> never visited</label>
        <label><input type="checkbox" checked={sp.has("never_messaged")} onChange={(e) => set("never_messaged", e.target.checked)} /> never messaged</label>
        <label><input type="checkbox" checked={sp.has("no_group")} onChange={(e) => set("no_group", e.target.checked)} /> not in any group</label>
        <button className="link" onClick={() => setHelp(!help)} aria-expanded={help}>{help ? "Hide search help" : "Search help"}</button>
      </div>
      {help && (
        <div className="panel" data-testid="search-help">
          <b>Boolean search</b> — works in the Search, Company, Position and Group boxes (they are combined with AND).
          <ul style={{ margin: "6px 0" }}>
            <li><code>AND</code>, <code>OR</code>, <code>NOT</code> (UPPERCASE), or <code>-word</code> to exclude; a space between words means AND; use <code>( )</code> to group.</li>
            <li><code>"exact phrase"</code> for several words together. Everything is a case-insensitive “contains” match.</li>
            <li><code>field:word</code> limits a word to <code>name</code>, <code>company</code>, <code>position</code> (or <code>title</code>) or <code>group</code>.</li>
          </ul>
          Examples — Search: <code>data AND (google OR acme) NOT manager</code> · <code>position:"product manager"</code> · <code>company:acme AND group:ml</code><br />
          Group box: <code>HR OR ML</code> (in either group) · <code>Hot AND NOT ML</code> (in Hot but not ML) · <code>NOT Hot</code> (not in Hot, including people in no group)
        </div>
      )}
      <div className="panel" data-testid="selection-bar">
        {selected.size === 0 ? (
          <div className="row">
            <span className="muted">Tick rows to add them to a group, export them, or mark them messaged.</span>
            <a href={`/api/export${qs(filterParams)}`}>{hasFilters ? `Export all ${total} matching CSV` : "Export all contacts CSV"}</a>
          </div>
        ) : (
          <>
            <div className="row">
              <b>{selected.size} selected</b>
              {allMatching ? <span className="muted">(all {total} matching the filters)</span>
                : total > items.length && selected.size >= items.length && <button className="link" onClick={selectAllMatching}>Select all {total} matching</button>}
              <button className="link" onClick={clearSelection}>Clear selection</button>
            </div>
            <div className="row">
              <select aria-label="Target group" value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">Choose group…</option>
                {groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
              <button disabled={!target || addToGroup.isPending} onClick={() => addToGroup.mutate()}>Add to group</button>
              <a href={allMatching ? `/api/export${qs(filterParams)}` : `/api/export?ids=${[...selected].join(",")}`} role="button">Export {selected.size} selected CSV</a>
              <button disabled={bulkMessaged.isPending} onClick={() => bulkMessaged.mutate()}>Mark {selected.size} messaged (now)</button>
            </div>
          </>
        )}
        {msg && <div className="toast">{msg}</div>}
      </div>
      {error && <p className="error">{(error as Error).message}</p>}
      <div className="table-wrap">
        <table className="contacts">
          <thead><tr>
            <th><input type="checkbox" aria-label="Select all on page" checked={items.length > 0 && items.every((c) => selected.has(c.id))} onChange={(e) => { setAllMatching(false); setSelected(e.target.checked ? new Set(items.map((c) => c.id)) : new Set()); }} /></th>
            {["name", "position", "company"].map((k) => <th key={k} className="sortable" onClick={() => sortBy(k)}>{label(k)}{sort === k ? (order === "asc" ? " ▲" : " ▼") : ""}</th>)}
            <th>LinkedIn</th>
            {["connected_on", "last_visited_at", "last_messaged_at"].map((k) => <th key={k} className="sortable" onClick={() => sortBy(k)}>{label(k)}{sort === k ? (order === "asc" ? " ▲" : " ▼") : ""}</th>)}
            <th>Groups</th><th>Messaged</th>
          </tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} className={selected.has(c.id) ? "selected" : ""}>
                <td><input type="checkbox" aria-label={`Select ${fullName(c)}`} checked={selected.has(c.id)} onChange={() => toggle(c.id)} /></td>
                <td><button className="link" onClick={() => setDrawer(c.id)}>{fullName(c)}</button></td>
                <td className="wrap">{c.position}</td><td className="wrap">{c.company}</td>
                <td className="url"><LinkedInLink id={c.id} url={c.linkedin_url} /></td>
                <td>{c.connected_on ?? "—"}</td><td title={fmtTs(c.last_visited_at)}>{fmtShort(c.last_visited_at)}</td><td title={fmtTs(c.last_messaged_at)}>{fmtShort(c.last_messaged_at)}</td>
                <td className="wrap">{c.groups.map((g) => <span className="badge" key={g.id}>{g.name}</span>)}</td>
                <td className="actions">
                  <button onClick={() => messaged.mutate({ id: c.id })}>Mark messaged</button>{" "}
                  <input type="date" aria-label={`Messaged date for ${fullName(c)}`} value={dates[c.id] ?? ""} onChange={(e) => setDates({ ...dates, [c.id]: e.target.value })} />
                  <button disabled={!dates[c.id]} onClick={() => dateInputToEpoch(dates[c.id]) && messaged.mutate({ id: c.id, date: dates[c.id] })}>Set</button>
                </td>
              </tr>
            ))}
            {!isLoading && items.length === 0 && <tr><td colSpan={11} className="muted">No contacts. <a href="/import">Import your connections</a>.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <button disabled={page === 0} onClick={() => set("page", String(page - 1))}>← Prev</button>
        <span>Page {page + 1} of {Math.max(1, Math.ceil(total / PAGE))}</span>
        <button disabled={(page + 1) * PAGE >= total} onClick={() => set("page", String(page + 1))}>Next →</button>
      </div>
      {drawer !== null && <ContactDrawer id={drawer} onClose={() => setDrawer(null)} />}
    </>
  );
}
