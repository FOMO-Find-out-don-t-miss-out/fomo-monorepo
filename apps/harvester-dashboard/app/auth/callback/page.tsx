'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, ShieldOff } from 'lucide-react';
import { getUserManager } from '@/lib/auth';

function getCallbackErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return 'Authentication failed. Please try again.';
  const msg = err.message;
  if (msg.includes('access_denied')) {
    return 'Access was denied. You may not have permission to use this application.';
  }
  if (msg.includes('No state in response') || msg.includes('No matching state')) {
    return 'Your sign-in session expired. Please try again.';
  }
  return 'Sign-in could not be completed. Please try again.';
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUserManager()
      .signinRedirectCallback()
      .then(() => router.replace('/'))
      .catch((err: unknown) => {
        // Log safe diagnostic info only — no tokens or user data
        console.error('[auth/callback] Sign-in callback failed:', err instanceof Error ? err.message : 'unknown error');
        setError(getCallbackErrorMessage(err));
      });
  }, [router]);

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6 bg-background text-center px-4">
        <ShieldOff className="h-10 w-10 text-destructive/50" />
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Sign-in failed</p>
          <p className="text-sm text-muted-foreground max-w-xs">{error}</p>
        </div>
        <a
          href="/login"
          className="px-4 py-2 rounded-lg bg-neon-blue/20 text-neon-blue hover:bg-neon-blue/30 text-sm font-medium transition-colors"
        >
          Back to login
        </a>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      <p className="text-sm text-muted-foreground">Completing sign-in…</p>
    </div>
  );
}
