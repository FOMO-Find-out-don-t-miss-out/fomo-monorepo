'use client';

import { type ReactNode } from 'react';
import { Loader2, ShieldOff } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';
import type { UserSystemRole } from '@/types/api';

interface RequireRoleProps {
  roles: UserSystemRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

function DefaultForbidden() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background text-muted-foreground">
      <ShieldOff className="h-12 w-12 text-destructive/50" />
      <p className="text-sm">You don&apos;t have permission to access this page.</p>
    </div>
  );
}

export function RequireRole({ roles, children, fallback }: RequireRoleProps) {
  const { fomoUser, isAuthenticated } = useAuth();

  // OIDC auth resolved but FOMO user is still being fetched from the API
  if (isAuthenticated && !fomoUser) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      </div>
    );
  }

  if (!fomoUser || !roles.includes(fomoUser.system_role)) {
    return fallback ?? <DefaultForbidden />;
  }

  return <>{children}</>;
}
