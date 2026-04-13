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
        'rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] no-underline transition',
        active
          ? 'border-[rgba(10,105,78,0.22)] bg-[var(--accent-soft)] text-[var(--accent-strong)]'
          : 'border-transparent bg-white/50 text-[var(--muted)] hover:border-[var(--line)] hover:bg-white/80 hover:text-[var(--ink)]',
      )}
    >
      {label}
    </Link>
  );
}

function currentViewLabel(pathname: string) {
  if (pathname === '/') return 'Welcome';
  if (pathname === '/dashboard') return 'Operations dashboard';
  if (pathname === '/settings') return 'Provider credentials';
  if (pathname === '/projects') return 'Projects';
  if (pathname === '/projects/new') return 'Create project';
  if (pathname === '/login') return 'Log in';
  if (pathname === '/signup') return 'Sign up';
  if (/^\/projects\/[^/]+\/models\/new$/.test(pathname)) return 'Upload model package';
  if (/^\/projects\/[^/]+\/cr\/new$/.test(pathname)) return 'New change request';
  if (/^\/projects\/[^/]+\/runs\/[^/]+$/.test(pathname)) return 'Workflow run';
  if (/^\/projects\/[^/]+$/.test(pathname)) return 'Project workspace';
  return 'ConstraintMod';
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
        { href: '/settings', label: 'Settings', active: pathname === '/settings' },
        ...(projectId
          ? [
              { href: `/projects/${projectId}`, label: 'Workspace', active: pathname === `/projects/${projectId}` },
              { href: `/projects/${projectId}/models/new`, label: 'Upload', active: pathname === `/projects/${projectId}/models/new` },
              { href: `/projects/${projectId}/cr/new`, label: 'Change request', active: pathname === `/projects/${projectId}/cr/new` },
            ]
          : []),
      ]
    : [];

  const showBackButton =
    isAuthed &&
    pathname !== '/' &&
    pathname !== '/dashboard' &&
    pathname !== '/settings' &&
    pathname !== '/projects' &&
    pathname !== '/login' &&
    pathname !== '/signup';

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6 sm:pt-5">
      <div className="mx-auto max-w-[118rem] rounded-[2rem] border border-[var(--line)] bg-[rgba(255,252,246,0.88)] px-4 py-4 shadow-[var(--shadow)] backdrop-blur-xl sm:px-5">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <Link href={isAuthed ? '/dashboard' : '/'} className="no-underline">
                <p className="eyebrow">Workflow control room</p>
              </Link>
              <p className="mt-2 max-w-3xl text-base text-[var(--muted)]">
                Structured uploads, transparent agent stages, and reviewable artifacts for every CP model modification run.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              {showBackButton ? (
                <Button type="button" className="border-[var(--line)] bg-[var(--ink)] shadow-none hover:bg-black" onClick={handleBack}>
                  Back
                </Button>
              ) : null}
              {loading ? (
                <span className="rounded-full border border-[var(--line)] bg-white/70 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                  Checking session
                </span>
              ) : isAuthed ? (
                <>
                  {userEmail ? (
                    <div className="rounded-[1rem] border border-[var(--line)] bg-white/75 px-3 py-2 text-right">
                      <p className="eyebrow">Signed in</p>
                      <p className="mt-1 text-sm text-[var(--ink)]">{userEmail}</p>
                    </div>
                  ) : null}
                  <Button type="button" onClick={handleLogout}>
                    Log out
                  </Button>
                </>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <NavLink href="/login" label="Log in" active={pathname === '/login'} />
                  <NavLink href="/signup" label="Sign up" active={pathname === '/signup'} />
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t border-[var(--line)] pt-3 md:flex-row md:items-center md:justify-between">
            <nav className="flex flex-wrap items-center gap-2">
              {navLinks.map((link) => (
                <NavLink key={link.href} href={link.href} label={link.label} active={link.active} />
              ))}
            </nav>
            <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
              <span className="status-dot" aria-hidden="true" />
              <span>{currentViewLabel(pathname)}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
