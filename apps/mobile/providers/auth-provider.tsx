import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { components } from '../types/api.generated';
import {
  clearTokens,
  exchangeRefreshToken,
  isTokenExpired,
  ISSUER,
  KEYCLOAK_CLIENT_ID,
  loadAccessToken,
  loadRefreshToken,
  REDIRECT_SCHEME,
  storeTokens,
} from '../utils/auth-client';

// Required for Android: closes the auth browser tab after redirect.
WebBrowser.maybeCompleteAuthSession();

// ── Types ─────────────────────────────────────────────────────────────────────

type UserMe = components['schemas']['UserMeResponse'];

export type LoginOptions = {
  /** Keycloak IdP alias to skip the realm login page and go straight to the provider. */
  idpHint?: string;
};

export interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserMe | null;
  accessToken: string | null;
  authError: string | null;
  login: (options?: LoginOptions) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');

async function fetchUserMe(accessToken: string): Promise<UserMe | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) {
      if (__DEV__) {
        const body = await res.text().catch(() => '(unreadable)');
        console.warn(`[auth] /users/me returned ${res.status}: ${body}`);
      }
      return null;
    }
    return (await res.json()) as UserMe;
  } catch (err) {
    if (__DEV__) console.warn('[auth] /users/me fetch error:', err);
    return null;
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Keycloak OIDC discovery (fetches /.well-known/openid-configuration)
  const discovery = AuthSession.useAutoDiscovery(ISSUER);

  // Must match Keycloak fomo-mobile client's valid redirect URI.
  // Provisioned in fomo-platform: fomo://auth/callback
  const redirectUri = AuthSession.makeRedirectUri({ scheme: REDIRECT_SCHEME, path: 'auth/callback' });

  useEffect(() => {
    if (__DEV__) console.log('[auth] redirect URI:', redirectUri);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [request, , promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: KEYCLOAK_CLIENT_ID,
      scopes: ['openid', 'email', 'profile', 'offline_access'],
      redirectUri,
      usePKCE: true,
      responseType: AuthSession.ResponseType.Code,
    },
    discovery,
  );

  // ── Internal session helpers ────────────────────────────────────────────────

  const applySession = useCallback(async (access: string, refresh?: string) => {
    await storeTokens(access, refresh);
    setAccessToken(access);
    const me = await fetchUserMe(access);
    setUser(me);
  }, []);

  const clearSession = useCallback(async () => {
    await clearTokens();
    setAccessToken(null);
    setUser(null);
  }, []);

  // ── Startup: restore session from SecureStore ───────────────────────────────

  useEffect(() => {
    (async () => {
      try {
        const refresh = await loadRefreshToken();
        if (refresh) {
          const refreshed = await exchangeRefreshToken(refresh);
          if (refreshed) {
            await applySession(refreshed.access, refreshed.refresh);
            return;
          }
          await clearTokens();
          return;
        }

        // No refresh token — check if stored access token is still valid.
        const access = await loadAccessToken();
        if (access && !isTokenExpired(access)) {
          setAccessToken(access);
          const me = await fetchUserMe(access);
          setUser(me);
        }
      } finally {
        setIsLoading(false);
      }
    })();
  }, [applySession]);

  // ── Login ────────────────────────────────────────────────────────────────────
  //
  // When idpHint is provided, we build the Keycloak authorization URL and append
  // `kc_idp_hint=<alias>` so Keycloak skips its login page and goes straight to
  // the identity provider. We pass the hinted URL to promptAsync via the `url`
  // override, so the PKCE flow (code challenge, verifier, token exchange) is
  // completely unchanged.

  const login = useCallback(async (options: LoginOptions = {}) => {
    if (!request || !discovery) return;
    setAuthError(null);

    try {
      let result: AuthSession.AuthSessionResult;

      if (options.idpHint) {
        // Build the standard authorization URL (code_challenge, state, nonce…)
        const baseUrl = await request.makeAuthUrlAsync(discovery);
        // Keycloak accepts kc_idp_hint as an extra query param — safe to append.
        const hintedUrl = `${baseUrl}&kc_idp_hint=${encodeURIComponent(options.idpHint)}`;
        result = await promptAsync({ url: hintedUrl });
      } else {
        result = await promptAsync();
      }

      if (result.type !== 'success') {
        if (result.type === 'error') setAuthError('Login failed. Please try again.');
        return;
      }

      const tokenResponse = await AuthSession.exchangeCodeAsync(
        {
          clientId: KEYCLOAK_CLIENT_ID,
          redirectUri,
          code: result.params.code,
          extraParams: { code_verifier: request.codeVerifier ?? '' },
        },
        discovery,
      );

      await applySession(tokenResponse.accessToken, tokenResponse.refreshToken ?? undefined);
    } catch {
      setAuthError('Login failed. Please try again.');
    }
  }, [request, discovery, promptAsync, redirectUri, applySession]);

  // ── Logout ───────────────────────────────────────────────────────────────────

  const logout = useCallback(async () => {
    setAuthError(null);
    await clearSession();
  }, [clearSession]);

  // ── Refresh session (public, used by callers that get a 401) ──────────────────

  const refreshSession = useCallback(async () => {
    const refresh = await loadRefreshToken();
    if (!refresh) {
      await clearSession();
      return;
    }
    const refreshed = await exchangeRefreshToken(refresh);
    if (refreshed) {
      await applySession(refreshed.access, refreshed.refresh);
    } else {
      await clearSession();
    }
  }, [applySession, clearSession]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!accessToken,
        isLoading,
        user,
        accessToken,
        authError,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
