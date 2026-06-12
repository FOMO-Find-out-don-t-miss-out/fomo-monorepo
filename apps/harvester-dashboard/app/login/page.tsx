'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';

export default function LoginPage() {
  const { isAuthenticated, isLoading, login } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.replace('/');
    } else {
      login();
    }
  }, [isLoading, isAuthenticated, login, router]);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
      <p className="text-sm text-muted-foreground">Redirecting to login…</p>
    </div>
  );
}
