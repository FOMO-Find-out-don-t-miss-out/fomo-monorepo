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

  const login = useCallback(async () => {
    await getUserManager().signinRedirect();
  }, []);

  const logout = useCallback(async () => {
    setFomoUser(null);
    setOidcUser(null);
    await getUserManager().signoutRedirect();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        oidcUser,
        fomoUser,
        isLoading,
        isAuthenticated: !!oidcUser,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
