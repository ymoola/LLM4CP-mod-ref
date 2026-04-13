'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { BrandLockup } from '@/components/brand-lockup';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api';

function SummaryCard({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: number;
  tone?: 'default' | 'success' | 'warning' | 'danger';
}) {
  return (
    <Card className="grid gap-4 rounded-[1.6rem] p-5">
      <p className="data-kicker">{label}</p>
      <div className="flex items-end justify-between gap-3">
        <p className="text-4xl font-semibold">{value}</p>
        <Badge tone={tone}>{label}</Badge>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const overviewQuery = useQuery({ queryKey: ['dashboard-overview'], queryFn: () => api.getDashboardOverview() });

  if (overviewQuery.isLoading) {
    return <p className="text-sm text-[var(--muted)]">Loading dashboard…</p>;
  }

  if (overviewQuery.error || !overviewQuery.data) {
    return <p className="text-sm text-rose-700">Unable to load your dashboard right now.</p>;
  }

  const { counts, recent_projects, recent_runs, runs_awaiting_clarification, runs_needing_review } = overviewQuery.data;
  const latestProject = recent_projects[0] ?? null;
  const clarificationRun = runs_awaiting_clarification[0] ?? null;

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
        <Card className="rounded-[2rem] border-[var(--line-strong)] bg-[linear-gradient(145deg,rgba(255,255,255,0.94),rgba(246,241,232,0.86))] p-6 sm:p-8">
          <div className="grid gap-8 xl:grid-cols-[1.2fr_0.9fr]">
            <div className="space-y-5">
              <div className="space-y-3">
                <p className="eyebrow">Operational home</p>
                <h1 className="max-w-3xl text-4xl leading-[0.98] sm:text-5xl">
                  Run CPMpy modification workflows with a transparent, auditable control surface.
                </h1>
                <p className="max-w-2xl text-sm text-[var(--muted)] sm:text-base">
                  This dashboard is your launchpad: validated packages, outstanding clarifications, recent runs, and exact model/provider choices all stay visible without digging through project folders.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link href="/projects/new" className="rounded-full bg-[var(--accent-strong)] px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.14em] text-white no-underline transition hover:bg-[var(--accent)]">
                  Create project
                </Link>
                <Link
                  href={latestProject ? `/projects/${latestProject.id}` : '/projects'}
                  className="rounded-full border border-[var(--line)] px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80"
                >
                  {latestProject ? 'Open latest project' : 'Browse projects'}
                </Link>
                {clarificationRun?.project_id ? (
                  <Link
                    href={`/projects/${clarificationRun.project_id}/runs/${clarificationRun.id}`}
                    className="rounded-full border border-[var(--line)] px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80"
                  >
                    Resume clarification
                  </Link>
                ) : null}
              </div>
            </div>

            <div className="grid gap-4">
              <BrandLockup size="hero" />
              <Card className="rounded-[1.5rem] bg-[linear-gradient(180deg,rgba(11,20,17,0.98),rgba(16,34,28,0.95))] p-5 text-white shadow-[var(--shadow-strong)]">
                <p className="eyebrow text-emerald-300">Research framing</p>
                <div className="mt-4 grid gap-4 text-sm text-slate-200">
                  <div>
                    <p className="text-base font-semibold text-white">Stage-separated modification pipeline</p>
                    <p className="mt-1 text-slate-300">
                      The workflow keeps parsing, clarification, planning, code modification, execution, and semantic validation as explicit stages so failures are attributable to a specific part of the pipeline.
                    </p>
                  </div>
                  <div>
                    <p className="text-base font-semibold text-white">Execution-backed evaluation</p>
                    <p className="mt-1 text-slate-300">
                      Runs record the chosen model, the effective runtime input, execution logs, and review status, which makes the generated output inspectable as a technical artifact rather than a chat response.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Badge tone={runs_awaiting_clarification.length ? 'warning' : 'default'}>
                      {runs_awaiting_clarification.length} awaiting clarification
                    </Badge>
                    <Badge tone={runs_needing_review.length ? 'warning' : 'default'}>
                      {runs_needing_review.length} need review
                    </Badge>
                    <Badge tone="success">{counts.validated_model_packages} validated packages</Badge>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <SummaryCard label="Projects" value={counts.total_projects} />
          <SummaryCard label="Validated packages" value={counts.validated_model_packages} tone="success" />
          <SummaryCard label="Completed runs" value={counts.completed_runs} tone="success" />
          <SummaryCard label="Needs review" value={counts.runs_needing_review} tone="warning" />
          <SummaryCard label="Failed runs" value={counts.failed_runs} tone="danger" />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="space-y-5 rounded-[1.9rem]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Recent projects</p>
              <h2 className="mt-2 text-2xl">Workspaces in motion</h2>
            </div>
            <Link href="/projects" className="text-sm no-underline">
              View all
            </Link>
          </div>
          {recent_projects.length ? (
            <div className="grid gap-4">
              {recent_projects.map((project, index) => (
                <div key={project.id} className="rounded-[1.4rem] border border-[var(--line)] bg-white/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="data-kicker">Project {String(index + 1).padStart(2, '0')}</p>
                      <Link href={`/projects/${project.id}`} className="mt-1 block text-xl font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                        {project.name}
                      </Link>
                    </div>
                    <span className="text-xs text-[var(--muted)]">{project.created_at ? new Date(project.created_at).toLocaleDateString() : ''}</span>
                  </div>
                  {project.description ? <p className="mt-3 text-sm text-[var(--muted)]">{project.description}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">No projects yet. Create one to upload your first model package.</p>
          )}
        </Card>

        <Card className="space-y-5 rounded-[1.9rem]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Recent runs</p>
              <h2 className="mt-2 text-2xl">Latest workflow output</h2>
            </div>
            <Link href="/projects" className="text-sm no-underline">
              Open projects
            </Link>
          </div>
          {recent_runs.length ? (
            <div className="grid gap-4">
              {recent_runs.map((run) => (
                <div key={run.id} className="rounded-[1.4rem] border border-[var(--line)] bg-white/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      {run.project_id ? (
                        <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="block text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                          {run.change_request_summary || 'Workflow run'}
                        </Link>
                      ) : (
                        <p className="text-lg font-semibold">{run.change_request_summary || 'Workflow run'}</p>
                      )}
                      <p className="mt-2 text-sm text-[var(--muted)]">
                        {run.model_provider} · {run.model_name} · {run.model_preset}
                      </p>
                    </div>
                    <Badge tone={run.status === 'completed' ? 'success' : run.status === 'needs_review' ? 'warning' : run.status === 'failed' ? 'danger' : 'default'}>
                      {run.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">No runs yet. Start from a validated model package and a change request.</p>
          )}
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card className="space-y-5 rounded-[1.9rem]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Human-in-the-loop</p>
              <h2 className="mt-2 text-2xl">Clarifications waiting on you</h2>
            </div>
            <Badge tone={runs_awaiting_clarification.length ? 'warning' : 'default'}>{runs_awaiting_clarification.length}</Badge>
          </div>
          {runs_awaiting_clarification.length ? (
            <div className="grid gap-4">
              {runs_awaiting_clarification.map((run) => (
                <div key={run.id} className="rounded-[1.4rem] border border-[var(--line)] bg-white/70 p-4">
                  {run.project_id ? (
                    <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                      {run.change_request_summary || 'Awaiting clarification'}
                    </Link>
                  ) : (
                    <p className="text-lg font-semibold">{run.change_request_summary || 'Awaiting clarification'}</p>
                  )}
                  <p className="mt-2 text-sm text-[var(--muted)]">{run.model_provider} · {run.model_name}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">Nothing is currently waiting on the clarification step.</p>
          )}
        </Card>

        <Card className="space-y-5 rounded-[1.9rem]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Manual review queue</p>
              <h2 className="mt-2 text-2xl">Executable runs that still need judgment</h2>
            </div>
            <Badge tone={runs_needing_review.length ? 'warning' : 'default'}>{runs_needing_review.length}</Badge>
          </div>
          {runs_needing_review.length ? (
            <div className="grid gap-4">
              {runs_needing_review.map((run) => (
                <div key={run.id} className="rounded-[1.4rem] border border-[var(--line)] bg-white/70 p-4">
                  {run.project_id ? (
                    <Link href={`/projects/${run.project_id}/runs/${run.id}`} className="text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                      {run.change_request_summary || 'Needs review'}
                    </Link>
                  ) : (
                    <p className="text-lg font-semibold">{run.change_request_summary || 'Needs review'}</p>
                  )}
                  <p className="mt-2 text-sm text-[var(--muted)]">{run.model_provider} · {run.model_name}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">No runs are currently waiting for manual review.</p>
          )}
        </Card>
      </section>
    </div>
  );
}
