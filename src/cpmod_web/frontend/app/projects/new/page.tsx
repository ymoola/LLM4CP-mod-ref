'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { api } from '../../../lib/api';
import { Button } from '../../../components/ui/button';
import { Card } from '../../../components/ui/card';
import { Input } from '../../../components/ui/input';
import { Textarea } from '../../../components/ui/textarea';

export default function NewProjectPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="grid max-w-3xl gap-6"
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
      <div className="page-intro">
        <p className="eyebrow">Workspace setup</p>
        <h1 className="text-4xl sm:text-5xl">Create a project</h1>
        <p>
          Projects keep model packages, change requests, workflow runs, and generated artifacts together so each modification effort has a clean audit trail.
        </p>
      </div>
      <Card className="grid gap-4 rounded-[1.9rem] p-6">
        <label className="grid gap-2">
          <span className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Project name</span>
          <Input name="name" placeholder="Assembly sequencing optimizer" required />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Short description</span>
          <Textarea name="description" placeholder="What models or modification work will this project contain?" />
        </label>
        {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        <div className="flex flex-wrap gap-3">
          <Button type="submit">Create project</Button>
        </div>
      </Card>
    </form>
  );
}
