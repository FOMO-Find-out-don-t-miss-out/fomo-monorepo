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

export interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserMe | null;
  authError: string | null;
  login: () => Promise<void>;
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
    if (!res.ok) return null;
    return (await res.json()) as UserMe;
  } catch {
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

  const redirectUri = AuthSession.makeRedirectUri({ scheme: REDIRECT_SCHEME });

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

  const login = useCallback(async () => {
    if (!request || !discovery) return;
    setAuthError(null);
    try {
      const result = await promptAsync();
      if (result.type !== 'success') {
        if (result.type === 'error') {
          setAuthError('Login failed. Please try again.');
        }
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
