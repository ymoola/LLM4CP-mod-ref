'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useMemo } from 'react';
import clsx from 'clsx';

import { useAuth } from '@/components/auth-provider';
import { Button } from '@/components/ui/button';

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={clsx(
        'rounded-full px-3 py-1.5 text-sm no-underline transition',
        active ? 'bg-emerald-100 text-emerald-900' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950',
      )}
    >
      {label}
    </Link>
  );
}

function currentViewLabel(pathname: string) {
  if (pathname === '/') return 'Home';
  if (pathname === '/dashboard') return 'Dashboard';
  if (pathname === '/projects') return 'Projects';
  if (pathname === '/projects/new') return 'Create project';
  if (pathname === '/login') return 'Log in';
  if (pathname === '/signup') return 'Sign up';
  if (/^\/projects\/[^/]+\/models\/new$/.test(pathname)) return 'Upload model package';
  if (/^\/projects\/[^/]+\/cr\/new$/.test(pathname)) return 'New change request';
  if (/^\/projects\/[^/]+\/runs\/[^/]+$/.test(pathname)) return 'Workflow run';
  if (/^\/projects\/[^/]+$/.test(pathname)) return 'Project workspace';
  return 'CP Mod Web';
}

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, isAuthed, userEmail, logout } = useAuth();

  const projectId = useMemo(() => {
    const match = pathname.match(/^\/projects\/([^/]+)/);
    return match ? match[1] : null;
  }, [pathname]);

  async function handleLogout() {
    await logout();
    router.push('/login');
    router.refresh();
  }

  function handleBack() {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
      return;
    }
    router.push('/dashboard');
  }

  const navLinks = isAuthed
    ? [
        { href: '/dashboard', label: 'Dashboard', active: pathname === '/dashboard' },
        { href: '/projects', label: 'Projects', active: pathname === '/projects' || pathname.startsWith('/projects/') },
        ...(projectId
          ? [
              { href: `/projects/${projectId}`, label: 'Current project', active: pathname === `/projects/${projectId}` },
              { href: `/projects/${projectId}/models/new`, label: 'Upload model', active: pathname === `/projects/${projectId}/models/new` },
              { href: `/projects/${projectId}/cr/new`, label: 'New change request', active: pathname === `/projects/${projectId}/cr/new` },
            ]
          : []),
      ]
    : [];

  const showBackButton =
    isAuthed &&
    pathname !== '/' &&
    pathname !== '/dashboard' &&
    pathname !== '/projects' &&
    pathname !== '/login' &&
    pathname !== '/signup';

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <Link href={isAuthed ? '/dashboard' : '/'} className="text-lg font-semibold text-slate-950 no-underline hover:text-emerald-800">
              CP Mod Web
            </Link>
            <nav className="flex flex-wrap items-center gap-2">
              {navLinks.map((link) => (
                <NavLink key={link.href} href={link.href} label={link.label} active={link.active} />
              ))}
            </nav>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {showBackButton ? (
              <Button type="button" className="bg-slate-900 hover:bg-slate-800" onClick={handleBack}>
                Back
              </Button>
            ) : null}
            {loading ? (
              <span className="text-sm text-slate-500">Checking session…</span>
            ) : isAuthed ? (
              <>
                {userEmail ? <span className="text-sm text-slate-600">{userEmail}</span> : null}
                <Button type="button" onClick={handleLogout}>
                  Log out
                </Button>
              </>
            ) : (
              <>
                <NavLink href="/login" label="Log in" active={pathname === '/login'} />
                <NavLink href="/signup" label="Sign up" active={pathname === '/signup'} />
              </>
            )}
          </div>
        </div>
        <p className="text-sm text-slate-500">{currentViewLabel(pathname)}</p>
      </div>
    </header>
  );
}
