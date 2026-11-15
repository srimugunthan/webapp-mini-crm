import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Contact } from "../types";
import { fullName } from "../util";

/** On tab refocus ask the server which visits are newer than last messaged (decision D24). */
export default function ReturnPrompt() {
  const loadedAt = useRef(Math.floor(Date.now() / 1000) - 5);
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [other, setOther] = useState(false);
  const [date, setDate] = useState("");
  const { data = [] } = useQuery({ queryKey: ["pending", "prompt"], queryFn: () => api.get<Contact[]>(`/api/visits/pending?since=${loadedAt.current}`) });

  useEffect(() => {
    const refetch = () => document.visibilityState !== "hidden" && qc.invalidateQueries({ queryKey: ["pending"] });
    window.addEventListener("focus", refetch);
    document.addEventListener("visibilitychange", refetch);
    return () => {
      window.removeEventListener("focus", refetch);
      document.removeEventListener("visibilitychange", refetch);
    };
  }, [qc]);

  const current = data.find((c) => !dismissed.has(c.id));
  if (!current) return null;

  const done = () => {
    setOther(false);
    setDate("");
    qc.invalidateQueries();
  };
  const mark = (d?: string) => api.send("POST", `/api/contacts/${current.id}/messaged`, d ? { date: d } : {}).then(done);
  const no = () => setDismissed(new Set(dismissed).add(current.id));

  return (
    <div className="overlay" role="dialog" aria-label="Return prompt">
      <div className="modal">
        <h1>Did you message {fullName(current)}?</h1>
        <p className="muted">You opened their LinkedIn profile from here.</p>
        <div className="row">
          <button className="primary" onClick={() => mark()}>Yes, just now</button>
          {!other && <button onClick={() => setOther(true)}>Yes, on another date</button>}
          <button onClick={no}>No</button>
        </div>
        {other && (
          <div className="row">
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="Date messaged" />
            <button disabled={!date} onClick={() => mark(date)}>Save date</button>
          </div>
        )}
      </div>
    </div>
  );
}
