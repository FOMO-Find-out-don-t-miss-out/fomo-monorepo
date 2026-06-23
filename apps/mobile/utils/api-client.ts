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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
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
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
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
