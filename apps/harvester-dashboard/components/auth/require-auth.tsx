'use client';

import { useEffect, type ReactNode } from 'react';
import { Loader2, ShieldOff } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';

interface RequireAuthProps {
  children: ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, isLoading, sessionExpired, login } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !sessionExpired) {
      login();
    }
  }, [isLoading, isAuthenticated, sessionExpired, login]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      </div>
    );
  }

  if (sessionExpired) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
        <ShieldOff className="h-10 w-10 text-destructive/50" />
        <div className="space-y-1 text-center">
          <p className="text-sm font-medium text-foreground">Your session has expired</p>
          <p className="text-xs text-muted-foreground">Please log in again to continue.</p>
        </div>
        <button
          onClick={login}
          className="px-4 py-2 rounded-lg bg-neon-blue/20 text-neon-blue hover:bg-neon-blue/30 text-sm font-medium transition-colors"
        >
          Log in again
        </button>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <>{children}</>;
}
