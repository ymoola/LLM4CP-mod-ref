'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { BrandLockup } from '../../../components/brand-lockup';
import { supabase } from '../../../lib/supabase';
import { Button } from '../../../components/ui/button';
import { Card } from '../../../components/ui/card';
import { Input } from '../../../components/ui/input';

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
      <Card className="rounded-[2rem] border-[var(--line-strong)] bg-[linear-gradient(145deg,rgba(255,255,255,0.95),rgba(246,242,233,0.86))] p-6 sm:p-8">
        <div className="space-y-6">
          <div className="space-y-3">
            <p className="eyebrow">Create your workspace</p>
            <h1 className="text-4xl leading-[0.98] sm:text-5xl">Sign up to manage model packages, change requests, and workflow runs.</h1>
            <p className="max-w-xl text-sm text-[var(--muted)] sm:text-base">
              Start with your own provider keys, upload a validated CPMpy base model, and keep every generated artifact tied to a concrete project record.
            </p>
          </div>
          <BrandLockup size="hero" priority />
        </div>
      </Card>

      <Card className="rounded-[2rem] p-6 sm:p-8">
        <form
          className="grid gap-4"
          action={async (fd) => {
            const email = String(fd.get('email') || '');
            const password = String(fd.get('password') || '');
            const { error } = await supabase.auth.signUp({ email, password });
            if (error) {
              setError(error.message);
              return;
            }
            router.push('/login');
          }}
        >
          <div>
            <p className="eyebrow">Authentication</p>
            <h2 className="mt-2 text-3xl">Create account</h2>
          </div>
          <Input name="email" type="email" placeholder="Email" required />
          <Input name="password" type="password" placeholder="Password" required />
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
          <Button type="submit">Create account</Button>
        </form>
      </Card>
    </div>
  );
}
