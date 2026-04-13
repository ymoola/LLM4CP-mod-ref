'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="mx-auto grid max-w-md gap-4"
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
      <h1 className="text-2xl font-semibold">Sign up</h1>
      <Input name="email" type="email" placeholder="Email" required />
      <Input name="password" type="password" placeholder="Password" required />
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="submit">Create account</Button>
    </form>
  );
}
