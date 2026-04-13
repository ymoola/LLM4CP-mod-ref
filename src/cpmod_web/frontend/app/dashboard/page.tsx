'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

function SummaryCard({ label, value, tone = 'default' }: { label: string; value: number; tone?: 'default' | 'success' | 'warning' | 'danger' }) {
  return (
    <Card className="space-y-2">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <div className="flex items-end justify-between gap-3">
        <p className="text-3xl font-semibold text-slate-950">{value}</p>
        <Badge tone={tone}>{label}</Badge>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const overviewQuery = useQuery({ queryKey: ['dashboard-overview'], queryFn: () => api.getDashboardOverview() });

  if (overviewQuery.isLoading) {
    return <p className="text-sm text-slate-600">Loading dashboard…</p>;
  }

  if (overviewQuery.error || !overviewQuery.data) {
    return <p className="text-sm text-rose-700">Unable to load your dashboard right now.</p>;
  }

  const { counts, recent_projects, recent_runs, runs_awaiting_clarification, runs_needing_review } = overviewQuery.data;
  const latestProject = recent_projects[0] ?? null;
  const clarificationRun = runs_awaiting_clarification[0] ?? null;

  return (
    <div className="space-y-8">
      <section className="grid gap-6 rounded-3xl bg-gradient-to-br from-emerald-950 via-slate-900 to-slate-800 px-6 py-8 text-white lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-4">
          <p className="text-sm uppercase tracking-[0.24em] text-emerald-200">Operational home</p>
          <div className="space-y-3">
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight">Run CPMpy modification workflows with a clear audit trail.</h1>
            <p className="max-w-2xl text-sm text-slate-200">
              Upload validated model packages, capture change requests in plain language, and track every planning, modification, execution, and review stage from one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/projects/new" className="rounded-full bg-emerald-400 px-4 py-2 text-sm font-medium text-slate-950 no-underline hover:bg-emerald-300">
              Create project
            </Link>
            <Link
              href={latestProject ? `/projects/${latestProject.id}` : '/projects'}
              className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white no-underline hover:bg-white/10"
            >
              {latestProject ? 'Open latest project' : 'Browse projects'}
            </Link>
            {clarificationRun?.project_id ? (
              <Link
                href={`/projects/${clarificationRun.project_id}/runs/${clarificationRun.id}`}
                className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white no-underline hover:bg-white/10"
              >
                Resume clarification
              </Link>
            ) : null}
            <Link href="/settings" className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white no-underline hover:bg-white/10">
              Manage API keys
            </Link>
          </div>
        </div>
        <Card className="border-white/10 bg-white/10 text-white shadow-none">
          <div className="space-y-3">
            <p className="text-sm font-medium text-emerald-200">Immediate attention</p>
            <div className="space-y-2 text-sm text-slate-100">
              <p>{runs_awaiting_clarification.length} run(s) awaiting clarification</p>
              <p>{runs_needing_review.length} run(s) ended in needs_review</p>
              <p>{counts.validated_model_packages} validated model package(s) ready to launch</p>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <SummaryCard label="Projects" value={counts.total_projects} />
        <SummaryCard label="Validated packages" value={counts.validated_model_packages} tone="success" />
        <SummaryCard label="Completed runs" value={counts.completed_runs} tone="success" />
        <SummaryCard label="Needs review" value={counts.runs_needing_review} tone="warning" />
        <SummaryCard label="Failed runs" value={counts.failed_runs} tone="danger" />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Recent projects</h2>
            <Link href="/projects" className="text-sm underline">View all</Link>
          </div>
          {recent_projects.length ? (
            <div className="space-y-3">
              {recent_projects.map((project) => (
                <div key={project.id} className="rounded-xl border border-slate-200 p-4">
                  <Link href={`/projects/${project.id}`} className="font-semibold text-slate-950 no-underline hover:text-emerald-800">
                    {project.name}
                  </Link>
                  {project.description ? <p className="mt-1 text-sm text-slate-600">{project.description}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No projects yet. Create one to upload your first model package.</p>
          )}
        </Card>

        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Recent runs</h2>
            <Link href="/projects" className="text-sm underline">Open projects</Link>
          </div>
          {recent_runs.length ? (
            <div className="space-y-3">
              {recent_runs.map((run) => (
                <div key={run.id} className="rounded-xl border border-slate-200 p-4">
                  {run.project_id ? (
                    <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="font-semibold text-slate-950 no-underline hover:text-emerald-800">
                      {run.change_request_summary || 'Workflow run'}
                    </Link>
                  ) : (
                    <p className="font-semibold text-slate-950">{run.change_request_summary || 'Workflow run'}</p>
                  )}
                  <p className="mt-1 text-sm text-slate-600">{run.model_provider} · {run.model_name} · {run.model_preset}</p>
                  <p className="text-sm text-slate-600">Status: {run.status}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No runs yet. Start from a validated model package and a change request.</p>
          )}
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Runs awaiting clarification</h2>
            <Badge tone={runs_awaiting_clarification.length ? 'warning' : 'default'}>{runs_awaiting_clarification.length}</Badge>
          </div>
          {runs_awaiting_clarification.length ? (
            <div className="space-y-3">
              {runs_awaiting_clarification.map((run) => (
                <div key={run.id} className="rounded-xl border border-slate-200 p-4">
                  {run.project_id ? (
                    <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="font-semibold text-slate-950 no-underline hover:text-emerald-800">
                      {run.change_request_summary || 'Awaiting clarification'}
                    </Link>
                  ) : (
                    <p className="font-semibold text-slate-950">{run.change_request_summary || 'Awaiting clarification'}</p>
                  )}
                  <p className="mt-1 text-sm text-slate-600">{run.model_provider} · {run.model_name}</p>
                  <p className="text-sm text-slate-600">Status: {run.status}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">Nothing is currently waiting on the human-in-the-loop step.</p>
          )}
        </Card>

        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Runs needing review</h2>
            <Badge tone={runs_needing_review.length ? 'warning' : 'default'}>{runs_needing_review.length}</Badge>
          </div>
          {runs_needing_review.length ? (
            <div className="space-y-3">
              {runs_needing_review.map((run) => (
                <div key={run.id} className="rounded-xl border border-slate-200 p-4">
                  {run.project_id ? (
                    <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="font-semibold text-slate-950 no-underline hover:text-emerald-800">
                      {run.change_request_summary || 'Needs review'}
                    </Link>
                  ) : (
                    <p className="font-semibold text-slate-950">{run.change_request_summary || 'Needs review'}</p>
                  )}
                  <p className="mt-1 text-sm text-slate-600">{run.model_provider} · {run.model_name}</p>
                  <p className="text-sm text-slate-600">Status: {run.status}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No runs are currently waiting for manual review.</p>
          )}
        </Card>
      </section>
    </div>
  );
}
