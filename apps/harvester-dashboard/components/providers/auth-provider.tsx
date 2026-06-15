'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { getUserManager, type OidcUser } from '@/lib/auth';
import type { UserMeResponse } from '@/types/api';

interface AuthContextValue {
  oidcUser: OidcUser | null;
  fomoUser: UserMeResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** True after an API 401 cleared the local session. Shows "Log in again" UI instead of auto-redirecting. */
  sessionExpired: boolean;
  /** True while signoutRedirect is in progress. Disables logout controls. */
  isLoggingOut: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [oidcUser, setOidcUser] = useState<OidcUser | null>(null);
  const [fomoUser, setFomoUser] = useState<UserMeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const fetchFomoUser = useCallback(async (accessToken: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        setFomoUser((await res.json()) as UserMeResponse);
      }
    } catch {
      // Non-critical: fall back to OIDC-only session; role checks will show forbidden
    }
  }, []);

  useEffect(() => {
    const manager = getUserManager();

    const onUserLoaded = async (user: OidcUser) => {
      setSessionExpired(false);
      setOidcUser(user);
      await fetchFomoUser(user.access_token);
    };

    const onUserUnloaded = () => {
      setOidcUser(null);
      setFomoUser(null);
    };

    manager.events.addUserLoaded(onUserLoaded);
    manager.events.addUserUnloaded(onUserUnloaded);

    (async () => {
      try {
        const user = await manager.getUser();
        if (user && !user.expired) {
          setOidcUser(user);
          await fetchFomoUser(user.access_token);
        }
      } finally {
        setIsLoading(false);
      }
    })();

    return () => {
      manager.events.removeUserLoaded(onUserLoaded);
      manager.events.removeUserUnloaded(onUserUnloaded);
    };
  }, [fetchFomoUser]);

  // Listen for API 401 events dispatched by lib/api.ts.
  // Clears local session and shows the "session expired" screen rather than
  // automatically redirecting to Keycloak, which can cause redirect loops when
  // the Keycloak session has also expired.
  useEffect(() => {
    const onExpired = () => {
      setOidcUser(null);
      setFomoUser(null);
      setSessionExpired(true);
    };
    window.addEventListener('fomo:session-expired', onExpired);
    return () => window.removeEventListener('fomo:session-expired', onExpired);
  }, []);

  const login = useCallback(async () => {
    setSessionExpired(false);
    await getUserManager().signinRedirect();
  }, []);

  const logout = useCallback(async () => {
    setIsLoggingOut(true);
    setFomoUser(null);
    setOidcUser(null);
    try {
      await getUserManager().signoutRedirect();
    } catch {
      setIsLoggingOut(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        oidcUser,
        fomoUser,
        isLoading,
        isAuthenticated: !!oidcUser,
        sessionExpired,
        isLoggingOut,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
