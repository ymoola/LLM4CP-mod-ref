'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { Card } from '@/components/ui/card';

export default function ProjectsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['projects'], queryFn: api.listProjects });
  if (isLoading) return <p>Loading projects…</p>;
  if (error) return <p>Unable to load projects.</p>;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Projects</h1>
        <Link href="/projects/new">New project</Link>
      </div>
      <div className="grid gap-4">
        {data?.map((project) => (
          <Card key={project.id}>
            <Link href={`/projects/${project.id}`} className="text-lg font-semibold">{project.name}</Link>
            <p className="mt-2 text-sm text-slate-700">{project.description || 'No description yet.'}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
