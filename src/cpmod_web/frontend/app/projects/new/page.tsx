'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export default function NewProjectPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="grid max-w-2xl gap-4"
      action={async (fd) => {
        try {
          const project = await api.createProject({
            name: String(fd.get('name') || ''),
            description: String(fd.get('description') || ''),
          });
          router.push(`/projects/${project.id}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unable to create project.');
        }
      }}
    >
      <h1 className="text-3xl font-semibold">Create project</h1>
      <Input name="name" placeholder="Project name" required />
      <Textarea name="description" placeholder="Short description" />
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="submit">Create project</Button>
    </form>
  );
}
