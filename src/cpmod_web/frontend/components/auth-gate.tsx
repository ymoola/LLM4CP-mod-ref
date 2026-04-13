'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useAuth } from '@/components/auth-provider';

const AUTH_ROUTES = new Set(['/login', '/signup']);

function isProtectedRoute(pathname: string) {
  return pathname === '/dashboard' || pathname === '/settings' || pathname.startsWith('/projects');
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, isAuthed } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (isProtectedRoute(pathname) && !isAuthed) {
      router.replace('/login');
      return;
    }
    if (AUTH_ROUTES.has(pathname) && isAuthed) {
      router.replace('/dashboard');
    }
  }, [loading, isAuthed, pathname, router]);

  if (loading && (isProtectedRoute(pathname) || AUTH_ROUTES.has(pathname))) {
    return <div className="py-16 text-center text-sm text-slate-600">Checking session…</div>;
  }

  if (!loading && isProtectedRoute(pathname) && !isAuthed) {
    return <div className="py-16 text-center text-sm text-slate-600">Redirecting to login…</div>;
  }

  if (!loading && AUTH_ROUTES.has(pathname) && isAuthed) {
    return <div className="py-16 text-center text-sm text-slate-600">Redirecting to dashboard…</div>;
  }

  return <>{children}</>;
}
