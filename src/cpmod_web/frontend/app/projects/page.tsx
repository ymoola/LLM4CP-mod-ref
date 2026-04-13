'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api';

export default function ProjectsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['projects'], queryFn: api.listProjects });

  if (isLoading) return <p className="text-sm text-[var(--muted)]">Loading projects…</p>;
  if (error) return <p className="text-sm text-rose-700">Unable to load projects.</p>;

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="page-intro">
          <p className="eyebrow">Project index</p>
          <h1 className="text-4xl sm:text-5xl">Model modification workspaces</h1>
          <p>
            Each project groups model packages, change requests, workflow runs, and their artifacts into one auditable workspace.
          </p>
        </div>
        <Link href="/projects/new" className="rounded-full bg-[var(--accent-strong)] px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.14em] text-white no-underline transition hover:bg-[var(--accent)]">
          New project
        </Link>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {data?.length ? (
          data.map((project, index) => (
            <Card key={project.id} className="grid gap-4 rounded-[1.9rem] p-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="data-kicker">Project {String(index + 1).padStart(2, '0')}</p>
                  <Link href={`/projects/${project.id}`} className="mt-2 block text-2xl font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                    {project.name}
                  </Link>
                </div>
                <Badge tone="default">Workspace</Badge>
              </div>
              <p className="text-sm text-[var(--muted)]">{project.description || 'No description yet.'}</p>
              <div className="flex items-center justify-between gap-3 border-t border-[var(--line)] pt-4">
                <span className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
                  {project.created_at ? new Date(project.created_at).toLocaleDateString() : 'New'}
                </span>
                <Link href={`/projects/${project.id}`} className="text-sm font-semibold no-underline">
                  Open workspace
                </Link>
              </div>
            </Card>
          ))
        ) : (
          <Card className="rounded-[1.9rem] p-8 md:col-span-2 xl:col-span-3">
            <p className="eyebrow">No projects yet</p>
            <h2 className="mt-3 text-3xl">Create your first workspace</h2>
            <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
              Start with a project, upload a validated model package, then issue change requests against that base model.
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
