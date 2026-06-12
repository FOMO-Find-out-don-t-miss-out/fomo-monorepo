'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { getUserManager } from '@/lib/auth';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUserManager()
      .signinRedirectCallback()
      .then(() => router.replace('/'))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Authentication failed';
        setError(msg);
      });
  }, [router]);

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
        <p className="text-sm text-destructive">{error}</p>
        <a href="/login" className="text-sm text-neon-blue hover:underline">
          Try again
        </a>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      <p className="text-sm text-muted-foreground">Completing login…</p>
    </div>
  );
}
