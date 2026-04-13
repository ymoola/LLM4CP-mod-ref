'use client';

import Link from 'next/link';

import { useAuth } from '@/components/auth-provider';
import { Button } from '@/components/ui/button';

export default function HomePage() {
  const { loading, isAuthed } = useAuth();

  return (
    <div className="space-y-6">
      <h1 className="text-4xl font-bold">CP Model Modification Web App</h1>
      <p className="max-w-2xl text-slate-700">
        Upload a CPMpy model package, describe a change in plain language, and inspect the workflow stage-by-stage.
      </p>
      {loading ? (
        <p className="text-sm text-slate-600">Checking session…</p>
      ) : isAuthed ? (
        <div className="flex gap-4">
          <Link href="/dashboard" className="no-underline">
            <Button type="button">Go to dashboard</Button>
          </Link>
          <Link href="/projects">Projects</Link>
        </div>
      ) : (
        <div className="flex gap-4">
          <Link href="/login" className="no-underline">
            <Button type="button">Log in</Button>
          </Link>
          <Link href="/signup">Sign up</Link>
        </div>
      )}
    </div>
  );
}
