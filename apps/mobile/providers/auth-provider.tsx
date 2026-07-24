import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
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
import { perfLog, perfMark, perfMilestone, perfSince } from '../utils/performance-debug';

// Required for Android: closes the auth browser tab after redirect.
WebBrowser.maybeCompleteAuthSession();

// ── Types ─────────────────────────────────────────────────────────────────────

type UserMe = components['schemas']['UserMeResponse'];

export type LoginOptions = {
  /** Keycloak IdP alias to skip the realm login page and go straight to the provider. */
  idpHint?: string;
};

// How the current session was established — instrumentation only (FOMO-179).
// Both 'returning' and 'first-bootstrap' get identical treatment: the backend
// provisions the local user idempotently from ANY authenticated endpoint
// (confirmed in packages/services user_identity_service — every protected
// route depends on the same get_or_create_from_identity as /users/me), so
// there is no client-observable "new vs existing FOMO user" signal and no
// safe/unsafe distinction to enforce here — this label just says which
// startup path produced the token, for log clarity.
export type SessionMode = 'returning' | 'first-bootstrap' | 'unauthenticated';

export interface AuthContextValue {
  isAuthenticated: boolean;
  /** Resolves as soon as a valid token exists (or is confirmed absent) — this
   * is what gates the protected app. Does NOT wait on /users/me (FOMO-179). */
  isLoading: boolean;
  /** True while /users/me is in flight for the current session. Scoped to
   * components that actually render profile fields (e.g. the Profile tab) —
   * never gates the rest of the app. */
  isProfileLoading: boolean;
  user: UserMe | null;
  /** Set when /users/me fails; distinct from authError (token-level failure).
   * A failure here does not mean the session is invalid — protected API
   * calls that need a local user row provision it themselves regardless. */
  profileError: string | null;
  accessToken: string | null;
  authError: string | null;
  sessionMode: SessionMode | null;
  login: (options?: LoginOptions) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  /** Re-attempt the background /users/me sync after a profileError. */
  retryProfileSync: () => void;
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
  const mark = perfMark();
  try {
    const res = await fetch(`${BASE_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    perfLog('request', {
      method: 'GET',
      endpoint: '/api/v1/users/me',
      duration_ms: perfSince(mark),
      status: res.status,
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
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [sessionMode, setSessionMode] = useState<SessionMode | null>(null);

  // Bumped on every logout and every new applySession call. The background
  // /users/me fetch checks this before committing its result, so a stale
  // response (superseded by logout or a new login before it resolves) can
  // never populate the wrong session — same closure-flag idiom used
  // elsewhere in this codebase (FOMO-176/177/178), generalized to a ref
  // since AuthProvider is a single long-lived instance, not remounted per
  // request.
  const sessionGenerationRef = useRef(0);

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
  //
  // FOMO-179: /users/me is never awaited on the path that resolves isLoading.
  // A valid token is sufficient to open the protected app — confirmed against
  // the backend that every protected endpoint (relationships, my-events)
  // provisions the local user itself via the same idempotent
  // get_or_create_from_identity that /users/me uses, so there is no ordering
  // requirement to preserve client-side. /users/me still runs, just in the
  // background, to populate `user` for the one screen that needs it
  // (Profile) — see isProfileLoading/profileError.

  const beginUserSync = useCallback((access: string, mode: SessionMode) => {
    sessionGenerationRef.current += 1;
    const generation = sessionGenerationRef.current;
    setIsProfileLoading(true);
    setProfileError(null);
    perfMilestone('user-bootstrap-start', { mode });

    fetchUserMe(access)
      .then((me) => {
        if (sessionGenerationRef.current !== generation) return; // superseded
        if (me) {
          setUser(me);
          perfMilestone('user-bootstrap-done', { mode, ok: true });
        } else {
          setProfileError('Failed to load profile');
          perfMilestone('user-bootstrap-done', { mode, ok: false });
        }
      })
      .finally(() => {
        if (sessionGenerationRef.current !== generation) return;
        setIsProfileLoading(false);
      });
  }, []);

  // access/refresh: token store. mode: instrumentation only (see SessionMode).
  // Does NOT touch `user` — a same-identity token refresh (refreshSession
  // after a 401) must not flash the Profile tab's already-loaded profile.
  // Callers that may represent a different identity (login) clear `user`
  // themselves first.
  const applySession = useCallback(async (
    access: string,
    refresh?: string,
    mode: SessionMode = 'returning',
  ) => {
    await storeTokens(access, refresh);
    setAccessToken(access);
    setSessionMode(mode);
    perfMilestone('token-ready', { mode });
    beginUserSync(access, mode);
  }, [beginUserSync]);

  const clearSession = useCallback(async () => {
    sessionGenerationRef.current += 1; // discard any in-flight background sync
    await clearTokens();
    setAccessToken(null);
    setUser(null);
    setIsProfileLoading(false);
    setProfileError(null);
    setSessionMode('unauthenticated');
  }, []);

  // ── Startup: restore session from SecureStore ───────────────────────────────

  useEffect(() => {
    (async () => {
      const bootMark = perfMark();
      let bootPath = 'no-session';
      try {
        const secureReadMark = perfMark();
        const refresh = await loadRefreshToken();
        perfLog('auth-bootstrap', {
          phase: 'secure-read',
          duration_ms: perfSince(secureReadMark),
          found: !!refresh,
        });

        if (refresh) {
          const exchangeMark = perfMark();
          const refreshed = await exchangeRefreshToken(refresh);
          perfLog('auth-bootstrap', {
            phase: 'refresh-exchange',
            duration_ms: perfSince(exchangeMark),
            ok: !!refreshed,
          });
          if (refreshed) {
            bootPath = 'refresh-exchange';
            await applySession(refreshed.access, refreshed.refresh, 'returning');
            return;
          }
          bootPath = 'refresh-failed';
          setSessionMode('unauthenticated');
          await clearTokens();
          return;
        }

        // No refresh token — check if stored access token is still valid.
        const access = await loadAccessToken();
        if (access && !isTokenExpired(access)) {
          bootPath = 'stored-access';
          setAccessToken(access);
          setSessionMode('returning');
          perfMilestone('token-ready', { mode: 'returning' });
          beginUserSync(access, 'returning');
        } else {
          setSessionMode('unauthenticated');
        }
      } finally {
        setIsLoading(false);
        perfMilestone('auth-bootstrap-resolved', {
          path: bootPath,
          duration_ms: perfSince(bootMark),
        });
      }
    })();
  }, [applySession, beginUserSync]);

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

      // A fresh interactive login may be a different identity than whatever
      // was cached before — clear it now rather than let it linger while the
      // new /users/me resolves in the background (security invariant: never
      // show a previous identity's profile after an identity change).
      setUser(null);
      setProfileError(null);
      await applySession(
        tokenResponse.accessToken,
        tokenResponse.refreshToken ?? undefined,
        'first-bootstrap',
      );
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
  //
  // Same identity continuing with a rotated token — does NOT clear `user`,
  // unlike login(), so a screen already showing profile data doesn't flash.

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

  // ── Retry background profile sync ───────────────────────────────────────────

  const retryProfileSync = useCallback(() => {
    if (!accessToken) return;
    beginUserSync(accessToken, sessionMode ?? 'returning');
  }, [accessToken, sessionMode, beginUserSync]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!accessToken,
        isLoading,
        isProfileLoading,
        user,
        profileError,
        accessToken,
        authError,
        sessionMode,
        login,
        logout,
        refreshSession,
        retryProfileSync,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
