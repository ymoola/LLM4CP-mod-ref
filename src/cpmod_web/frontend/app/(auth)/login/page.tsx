'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="mx-auto grid max-w-md gap-4"
      action={async (fd) => {
        const email = String(fd.get('email') || '');
        const password = String(fd.get('password') || '');
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          setError(error.message);
          return;
        }
        if (data.session?.access_token) {
          localStorage.setItem('cpmod-access-token', data.session.access_token);
        }
        router.push('/dashboard');
      }}
    >
      <h1 className="text-2xl font-semibold">Log in</h1>
      <Input name="email" type="email" placeholder="Email" required />
      <Input name="password" type="password" placeholder="Password" required />
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="submit">Log in</Button>
    </form>
  );
}
