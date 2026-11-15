import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, qs } from "../api";
import type { Group, ImportSummary } from "../types";
import Modal from "../components/Modal";

interface Stats { contacts: number; groups: number; memberships: number; notes: number; stage_history: number; templates: number }
interface RestorePreview { schema_version: number; app_schema_version: number; needs_upgrade: boolean; contacts: number; groups: number; memberships: number; notes: number; stage_history: number; templates: number }
interface RestoreResult { restored: boolean; contacts: number; groups: number; notes: number; upgraded: boolean; safety_backup: string }
type Result = ImportSummary & { fresh?: boolean; backup?: string | null; deleted?: Stats; group?: { id: number; name: string; created: boolean; added: number; already_members: number } };

const PHRASE = "RESET";
const RESTORE_PHRASE = "RESTORE";

export default function ImportPage() {
  const qc = useQueryClient();
  const addFile = useRef<HTMLInputElement>(null);
  const freshFile = useRef<HTMLInputElement>(null);
  const [summary, setSummary] = useState<Result | null>(null);
  const [confirming, setConfirming] = useState<File | null>(null);
  const [typed, setTyped] = useState("");
  const [localErr, setLocalErr] = useState("");
  const [groupName, setGroupName] = useState("");
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups") });
  const restoreFile = useRef<HTMLInputElement>(null);
  const [restoring, setRestoring] = useState<{ file: File; info: RestorePreview } | null>(null);
  const [restoreTyped, setRestoreTyped] = useState("");
  const [restored, setRestored] = useState<RestoreResult | null>(null);
  const preview = useMutation({
    mutationFn: (f: File) => api.upload<RestorePreview>("/api/restore/preview", f).then((info) => ({ file: f, info })),
    onSuccess: (r) => { setRestoring(r); setRestoreTyped(""); }, onMutate: () => { setRestored(null); setLocalErr(""); },
  });
  const restore = useMutation({
    mutationFn: (f: File) => api.upload<RestoreResult>(`/api/restore${qs({ confirm: RESTORE_PHRASE })}`, f),
    onSuccess: (r) => { setRestored(r); setRestoring(null); setRestoreTyped(""); setSummary(null); qc.invalidateQueries(); },
    onError: () => setRestoring(null),
  });

  const done = (s: Result) => { setSummary(s); setConfirming(null); setTyped(""); qc.invalidateQueries(); };
  const add = useMutation({
    mutationFn: (f: File) => api.upload<Result>(`/api/import${qs({ group: groupName.trim() })}`, f),
    onSuccess: (r) => { done(r); setGroupName(""); }, onMutate: () => { setSummary(null); setLocalErr(""); },
  });
  const fresh = useMutation({
    mutationFn: (f: File) => api.upload<Result>(`/api/import${qs({ mode: "fresh", confirm: PHRASE })}`, f),
    onSuccess: done, onMutate: () => { setSummary(null); setLocalErr(""); },
    onError: () => setConfirming(null),
  });
  const stats = useQuery({ queryKey: ["import-stats"], queryFn: () => api.get<Stats>("/api/import/stats"), enabled: confirming !== null, staleTime: 0 });
  const err = (add.error ?? fresh.error ?? preview.error ?? restore.error) as Error | null;

  const startFresh = () => {
    const f = freshFile.current?.files?.[0];
    if (!f) return setLocalErr("Choose a CSV file for the fresh import first.");
    setLocalErr(""); setTyped(""); setConfirming(f);
  };
  const s = stats.data;
  const currentStats = useQuery({ queryKey: ["import-stats", "restore"], queryFn: () => api.get<Stats>("/api/import/stats"), enabled: restoring !== null, staleTime: 0 });

  return (
    <>
      <h1>Import connections</h1>
      <p className="muted">A copy of every CSV you upload anywhere in the app is also saved in the <code>data/</code> folder (up to 25 MB per file).</p>

      <div className="panel">
        <h2>Add to existing contacts</h2>
        <p className="muted">Upload any connections CSV (a LinkedIn export, or a file with the same columns). New people are added and people you already have are updated, matched by LinkedIn URL.
          <b> Nothing is deleted</b>: groups, stages, notes, and visited/messaged dates are kept, and contacts missing from the file stay.</p>
        <div className="row">
          <input ref={addFile} type="file" accept=".csv,text/csv" aria-label="CSV to add" />
        </div>
        <div className="row">
          <label>Group name <span className="muted">(optional)</span>{" "}
            <input list="existing-groups" value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="e.g. Following" aria-label="Group name for this upload" maxLength={100} size={24} />
          </label>
          <datalist id="existing-groups">{groups.data?.map((g) => <option key={g.id} value={g.name} />)}</datalist>
          <button className="primary" disabled={add.isPending} onClick={() => addFile.current?.files?.[0] && add.mutate(addFile.current.files[0])}>Upload and add to contacts</button>
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>Leave the group name empty to just add people to your contacts (for example, new connections).
          Type a name such as <b>Following</b> to also put everyone in the file into that group; it is created if it doesn't exist (without a pipeline), or reused if it does.
          Everyone still appears in Contacts either way.</p>
      </div>

      <div className="panel" style={{ borderColor: "var(--warn)" }}>
        <h2 className="warn">Fresh import — replaces everything</h2>
        <p className="muted">A complete reset: deletes <b>all</b> current contacts, groups, stages, stage history, notes and your pipeline templates (the default Starter template is re-created),
          then loads this file as your only connections. A backup of the current database is saved first, and you will be asked to confirm.</p>
        <div className="row">
          <input ref={freshFile} type="file" accept=".csv,text/csv" aria-label="CSV for fresh import" />
          <button className="danger" disabled={fresh.isPending} onClick={startFresh}>Upload and Fresh import</button>
        </div>
      </div>

      <div className="panel" style={{ borderColor: "var(--warn)" }}>
        <h2 className="warn">Restore database from a .sqlite backup</h2>
        <p className="muted">Replaces <b>everything</b> (contacts, groups, stages, notes, pipeline templates) with the contents of a backup file made by this app
          (for example from <i>Download backup</i> below, or a file in <code>db/backups/</code>). You'll see what the file contains before anything changes,
          and your current data is saved to <code>db/backups/</code> first.</p>
        <div className="row">
          <input ref={restoreFile} type="file" accept=".sqlite,.db,application/octet-stream" aria-label="SQLite backup file" />
          <button className="danger" disabled={preview.isPending} onClick={() => { const f = restoreFile.current?.files?.[0]; f ? preview.mutate(f) : setLocalErr("Choose a .sqlite backup file first."); }}>Upload and restore database</button>
        </div>
      </div>

      <div className="panel">
        <h2>Backup</h2>
        <p className="muted">Download a consistent copy of your whole database (all contacts, groups, stages, notes).</p>
        <a href="/api/backup" download>Download backup</a>
      </div>

      {(err || localErr) && <p className="error" role="alert">{localErr || err!.message}</p>}
      {restored && (
        <div className="panel" data-testid="restore-summary">
          <h2>Database restored</h2>
          <p>Now holding <b>{restored.contacts}</b> contacts, <b>{restored.groups}</b> groups and <b>{restored.notes}</b> notes.{restored.upgraded ? " The backup was from an older version and has been upgraded." : ""}</p>
          <p className="muted">Your previous data was saved as <code>db/backups/{restored.safety_backup}</code>.</p>
          <Link to="/">View contacts →</Link>
        </div>
      )}
      {summary && (
        <div className="panel" data-testid="import-summary">
          <h2>{summary.fresh ? "Fresh import done" : "Import summary"}</h2>
          <p><b>{summary.new}</b> new · <b>{summary.updated}</b> updated · <b>{summary.skipped.length}</b> skipped · <b>{summary.errors.length}</b> errors</p>
          {summary.group && (
            <p>Group <b>{summary.group.name}</b>{summary.group.created ? " was created" : " already existed"}: <b>{summary.group.added}</b> people added{summary.group.already_members ? `, ${summary.group.already_members} were already in it` : ""}.{" "}
              <Link to={`/groups/${summary.group.id}`}>Open group →</Link></p>
          )}
          {summary.fresh && summary.deleted && (
            <p className="muted">Replaced {summary.deleted.contacts} contacts, {summary.deleted.groups} groups and {summary.deleted.notes} notes.
              {summary.backup ? <> Backup of the old data: <code>db/backups/{summary.backup}</code>.</> : null}</p>
          )}
          {summary.skipped.length > 0 && <ul>{summary.skipped.map((x) => <li key={x.row}>Row {x.row}{x.name ? ` (${x.name})` : ""}: {x.reason}</li>)}</ul>}
          <Link to="/">View contacts →</Link>
        </div>
      )}

      {restoring && (
        <Modal title="Replace your database with this backup?" onClose={() => setRestoring(null)}>
          <p className="error" style={{ marginTop: 0 }}><b>This overwrites your database.</b></p>
          <p>The file <code>{restoring.file.name}</code> contains <b>{restoring.info.contacts}</b> contacts, <b>{restoring.info.groups}</b> groups ({restoring.info.memberships} memberships),
            <b> {restoring.info.notes}</b> notes and <b>{restoring.info.templates}</b> pipeline templates.</p>
          <p>Your <b>current</b> data{currentStats.data ? <> (<b>{currentStats.data.contacts}</b> contacts, <b>{currentStats.data.groups}</b> groups, <b>{currentStats.data.notes}</b> notes)</> : null} will be replaced.
            {restoring.info.needs_upgrade ? " This backup is from an older version and will be upgraded." : ""}</p>
          <p className="muted">A backup of your current database is saved to <code>db/backups/</code> first. If anything fails, your current data is kept.</p>
          <p>Type <b>{RESTORE_PHRASE}</b> to confirm:</p>
          <div className="row">
            <input aria-label="Type RESTORE to confirm" autoFocus value={restoreTyped} onChange={(e) => setRestoreTyped(e.target.value)} placeholder={RESTORE_PHRASE}
              onKeyDown={(e) => e.key === "Enter" && restoreTyped === RESTORE_PHRASE && restore.mutate(restoring.file)} />
            <button className="danger" disabled={restoreTyped !== RESTORE_PHRASE || restore.isPending} onClick={() => restore.mutate(restoring.file)}>Replace database</button>
            <button onClick={() => setRestoring(null)}>Cancel</button>
          </div>
        </Modal>
      )}

      {confirming && (
        <Modal title="Replace all your data?" onClose={() => setConfirming(null)}>
          <p className="error" style={{ marginTop: 0 }}><b>This overwrites your database.</b></p>
          <p>Importing <code>{confirming.name}</code> as a <b>fresh import</b> will permanently delete
            {s ? <> <b>{s.contacts}</b> contacts, <b>{s.groups}</b> groups ({s.memberships} memberships), <b>{s.notes}</b> notes, <b>{s.stage_history}</b> stage-history entries and <b>{s.templates}</b> pipeline templates</> : " your current data"} and
            replace them with the contents of this file. Only the default Starter pipeline template is re-created.</p>
          <p className="muted">A backup of the current database is saved to <code>db/backups/</code> first, and if the file fails to import nothing is deleted.</p>
          <p>Type <b>{PHRASE}</b> to confirm:</p>
          <div className="row">
            <input aria-label="Type RESET to confirm" autoFocus value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={PHRASE}
              onKeyDown={(e) => e.key === "Enter" && typed === PHRASE && fresh.mutate(confirming)} />
            <button className="danger" disabled={typed !== PHRASE || fresh.isPending} onClick={() => fresh.mutate(confirming)}>Delete everything and import</button>
            <button onClick={() => setConfirming(null)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  );
}
