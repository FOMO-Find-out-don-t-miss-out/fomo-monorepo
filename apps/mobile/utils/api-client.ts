import { perfEnabled, perfLog, perfMark, perfSince } from './performance-debug';

const BASE_URL = (
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_API_URL ?? ''
).replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ── Perf instrumentation (no-op unless EXPO_PUBLIC_PERF_DEBUG=true) ──────────

// Strip query string and collapse UUID path segments so logs never contain
// event IDs or personal data — only the route shape.
function normalizeEndpoint(path: string): string {
  const qIndex = path.indexOf('?');
  const base = qIndex === -1 ? path : path.slice(0, qIndex);
  return base.replace(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi,
    ':id',
  );
}

function logRequest(
  method: string,
  path: string,
  mark: number,
  status: number | 'network-error',
  res?: Response,
): void {
  if (!perfEnabled) return;
  // Batch size of ?event_ids=… requests, logged as a count (never the IDs).
  const idBatch = (path.match(/event_ids=/g) ?? []).length;
  const contentLength = res?.headers.get('content-length');
  perfLog('request', {
    method,
    endpoint: normalizeEndpoint(path),
    duration_ms: perfSince(mark),
    status,
    id_batch: idBatch > 0 ? idBatch : undefined,
    query_len: path.includes('?') ? path.length - path.indexOf('?') : undefined,
    bytes: contentLength ?? undefined,
  });
}

async function instrumentedFetch(
  path: string,
  init: RequestInit,
): Promise<Response> {
  const method = init.method ?? 'GET';
  const mark = perfMark();
  try {
    const res = await fetch(`${BASE_URL}${path}`, init);
    logRequest(method, path, mark, res.status, res);
    return res;
  } catch (err) {
    logRequest(method, path, mark, 'network-error');
    throw err;
  }
}

// ── Public API helpers ────────────────────────────────────────────────────────

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await instrumentedFetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function apiFetchAuth<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const res = await instrumentedFetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Session expired. Please log in again.');
  }
  if (!res.ok) {
    if (__DEV__) {
      const body = await res.clone().text().catch(() => '(unreadable)');
      console.warn(`[api] ${init?.method ?? 'GET'} ${path} → ${res.status}: ${body}`);
    }
    throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
