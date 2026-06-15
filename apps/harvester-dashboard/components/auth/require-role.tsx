'use client';

import { type ReactNode } from 'react';
import Link from 'next/link';
import { Loader2, ShieldOff } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';
import type { UserSystemRole } from '@/types/api';

interface RequireRoleProps {
  roles: UserSystemRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

function formatRole(role: UserSystemRole): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

interface DefaultForbiddenProps {
  email?: string;
  role?: UserSystemRole;
  logout: () => Promise<void>;
}

function DefaultForbidden({ email, role, logout }: DefaultForbiddenProps) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-6 bg-background text-center px-4">
      <ShieldOff className="h-12 w-12 text-destructive/50" />
      <div className="space-y-2">
        <p className="text-base font-medium text-foreground">Access restricted</p>
        <p className="text-sm text-muted-foreground max-w-xs">
          You don&apos;t have the required permissions to view this page.
        </p>
        {email && (
          <p className="text-xs text-muted-foreground">
            Signed in as{' '}
            <span className="font-mono">{email}</span>
            {role && <> &middot; {formatRole(role)}</>}
          </p>
        )}
      </div>
      <div className="flex gap-3">
        <Link
          href="/"
          className="px-4 py-2 rounded-lg bg-muted/20 text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          Back to dashboard
        </Link>
        <button
          onClick={logout}
          className="px-4 py-2 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 text-sm transition-colors"
        >
          Log out
        </button>
      </div>
    </div>
  );
}

export function RequireRole({ roles, children, fallback }: RequireRoleProps) {
  const { fomoUser, isAuthenticated, oidcUser, logout } = useAuth();

  // OIDC auth resolved but FOMO user is still being fetched from the API
  if (isAuthenticated && !fomoUser) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      </div>
    );
  }

  if (!fomoUser || !roles.includes(fomoUser.system_role)) {
    if (fallback) return <>{fallback}</>;
    const email = fomoUser?.email ?? (oidcUser?.profile?.email as string | undefined) ?? undefined;
    return (
      <DefaultForbidden
        email={email}
        role={fomoUser?.system_role}
        logout={logout}
      />
    );
  }

  return <>{children}</>;
}
