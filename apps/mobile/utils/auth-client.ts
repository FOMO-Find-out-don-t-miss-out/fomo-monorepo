import * as SecureStore from 'expo-secure-store';

// ── Configuration ─────────────────────────────────────────────────────────────

export const AUTH_BASE_URL = (process.env.EXPO_PUBLIC_AUTH_URL ?? '').replace(/\/$/, '');
export const KEYCLOAK_REALM = process.env.EXPO_PUBLIC_KEYCLOAK_REALM ?? 'fomo-admin';
export const KEYCLOAK_CLIENT_ID = process.env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID ?? 'fomo-mobile';
export const REDIRECT_SCHEME = process.env.EXPO_PUBLIC_AUTH_REDIRECT_SCHEME ?? 'fomo';

export const ISSUER = `${AUTH_BASE_URL}/realms/${KEYCLOAK_REALM}`;

// ── Secure storage ────────────────────────────────────────────────────────────

const KEY_ACCESS = 'fomo_access_token';
const KEY_REFRESH = 'fomo_refresh_token';

export async function storeTokens(access: string, refresh?: string): Promise<void> {
  await SecureStore.setItemAsync(KEY_ACCESS, access);
  if (refresh) await SecureStore.setItemAsync(KEY_REFRESH, refresh);
}

export const loadAccessToken = (): Promise<string | null> =>
  SecureStore.getItemAsync(KEY_ACCESS);

export const loadRefreshToken = (): Promise<string | null> =>
  SecureStore.getItemAsync(KEY_REFRESH);

export async function clearTokens(): Promise<void> {
  await Promise.allSettled([
    SecureStore.deleteItemAsync(KEY_ACCESS),
    SecureStore.deleteItemAsync(KEY_REFRESH),
  ]);
}

// ── JWT expiry (no library — avoids extra dependency) ─────────────────────────

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')),
    );
    return typeof payload.exp !== 'number' || Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

// ── Token refresh ─────────────────────────────────────────────────────────────

export interface RefreshedTokens {
  access: string;
  refresh: string;
}

export async function exchangeRefreshToken(
  refreshToken: string,
): Promise<RefreshedTokens | null> {
  try {
    const res = await fetch(`${ISSUER}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: KEYCLOAK_CLIENT_ID,
        refresh_token: refreshToken,
      }).toString(),
    });
    if (!res.ok) return null;
    const data: { access_token: string; refresh_token?: string } = await res.json();
    return {
      access: data.access_token,
      refresh: data.refresh_token ?? refreshToken,
    };
  } catch {
    return null;
  }
}
