export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : (detail as { message?: string })?.message ?? `Request failed (${status})`);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? res.statusText);
  return body as T;
}

export const api = {
  get: <T>(url: string) => fetch(url).then((r) => handle<T>(r)),
  send: <T>(method: string, url: string, body?: unknown) =>
    fetch(url, { method, headers: body === undefined ? {} : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) }).then((r) => handle<T>(r)),
  upload: <T>(url: string, file: File, extra: Record<string, string> = {}) => {
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    return fetch(url, { method: "POST", body: fd }).then((r) => handle<T>(r));
  },
};

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) s.set(k, String(v));
  });
  const out = s.toString();
  return out ? `?${out}` : "";
}
