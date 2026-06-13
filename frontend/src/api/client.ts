// Thin fetch wrapper around the FastAPI backend.
// In dev, BASE is "" and Vite proxies the known paths to localhost:8000.
// In prod, set VITE_API_BASE_URL to the deployed API origin.

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body);
    } catch {
      /* non-JSON error body — keep statusText */
    }
    throw new Error(`${res.status} — ${detail}`);
  }
  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string): Promise<T> {
  return fetch(`${BASE}${path}`).then((r) => handle<T>(r));
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then((r) => handle<T>(r));
}

export function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  return fetch(`${BASE}${path}`, { method: "POST", body: form }).then((r) =>
    handle<T>(r)
  );
}
