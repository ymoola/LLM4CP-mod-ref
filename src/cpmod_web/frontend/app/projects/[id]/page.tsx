'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../../../lib/api';
import { Badge } from '../../../components/ui/badge';
import { Button } from '../../../components/ui/button';
import { Card } from '../../../components/ui/card';

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const packagesQuery = useQuery({
    queryKey: ['model-packages', params.id],
    queryFn: () => api.listModelPackages(params.id),
    refetchInterval: (query) => {
      const packages = query.state.data ?? [];
      return packages.some((pkg) => pkg.validation_status === 'running') ? 2000 : false;
    },
  });
  const crQuery = useQuery({ queryKey: ['change-requests', params.id], queryFn: () => api.listChangeRequests(params.id) });
  const runsQuery = useQuery({ queryKey: ['project-runs', params.id], queryFn: () => api.listProjectRuns(params.id) });
  const packageLookup = new Map((packagesQuery.data ?? []).map((pkg) => [pkg.id, pkg]));

  const deleteProjectMutation = useMutation({
    mutationFn: () => api.deleteProject(params.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
      router.push('/projects');
      router.refresh();
    },
  });

  function handleDeleteProject() {
    if (
      !window.confirm(
        'Delete this project and all of its model packages, change requests, workflow runs, and artifacts? This cannot be undone.',
      )
    ) {
      return;
    }
    deleteProjectMutation.mutate();
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
        <div className="page-intro">
          <p className="eyebrow">Project workspace</p>
          <h1 className="text-4xl sm:text-5xl">Model packages, change requests, and workflow runs in one place</h1>
          <p>
            This workspace becomes the operational record for one stream of model modification work: validated uploads, natural-language requests, and every run artifact tied together.
          </p>
        </div>
        <Card className="flex flex-wrap items-center justify-end gap-3 rounded-[1.9rem] p-5">
          <Link
            href={`/projects/${params.id}/models/new`}
            className="rounded-full border border-[var(--line)] px-4 py-2 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80"
          >
            Upload model package
          </Link>
          <Link
            href={`/projects/${params.id}/cr/new`}
            className="rounded-full border border-[var(--line)] px-4 py-2 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80"
          >
            New change request
          </Link>
          <Button type="button" className="bg-red-700 hover:bg-red-800" disabled={deleteProjectMutation.isPending} onClick={handleDeleteProject}>
            {deleteProjectMutation.isPending ? 'Deleting project…' : 'Delete project'}
          </Button>
          {deleteProjectMutation.isError ? (
            <p className="w-full text-sm text-red-700">
              {deleteProjectMutation.error instanceof Error ? deleteProjectMutation.error.message : 'Unable to delete project.'}
            </p>
          ) : null}
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Inventory</p>
            <h2 className="mt-2 text-3xl">Model packages</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {packagesQuery.data?.length ?? 0} package{(packagesQuery.data?.length ?? 0) === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <div className="grid gap-4">
          {packagesQuery.data?.length ? (
            packagesQuery.data.map((pkg) => (
              <Card key={pkg.id} className="rounded-[1.7rem]">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <Link href={`/projects/${params.id}/model-packages/${pkg.id}`} className="text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                      {pkg.filename}
                    </Link>
                    <p className="mt-2 text-sm text-[var(--muted)]">Validation: {pkg.validation_status}</p>
                  </div>
                  <Badge tone={pkg.validation_status === 'validated' ? 'success' : pkg.validation_status === 'failed' ? 'danger' : 'warning'}>
                    {pkg.validation_status}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Execution mode: {String(pkg.metadata.execution_mode || 'script')}
                  {pkg.metadata.entrypoint_name ? ` · Entrypoint: ${String(pkg.metadata.entrypoint_name)}` : ''}
                </p>
                <p className="text-sm text-[var(--muted)]">{pkg.validation_summary || 'Awaiting validation summary.'}</p>
              </Card>
            ))
          ) : (
            <Card className="rounded-[1.7rem]">
              <p className="text-sm text-[var(--muted)]">No model packages uploaded yet.</p>
            </Card>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Request queue</p>
            <h2 className="mt-2 text-3xl">Change requests</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {crQuery.data?.length ?? 0} request{(crQuery.data?.length ?? 0) === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <div className="grid gap-4">
          {crQuery.data?.length ? (
            crQuery.data.map((cr) => (
              <Card key={cr.id} className="rounded-[1.7rem]">
                <Link href={`/projects/${params.id}/change-requests/${cr.id}`} className="text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                  {cr.what_should_change}
                </Link>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Base model: {cr.model_package_filename || packageLookup.get(cr.model_package_id)?.filename || 'Unknown package'}
                </p>
                <p className="text-sm text-[var(--muted)]">
                  Runtime input: {cr.override_input_data_filename ? `Override file (${cr.override_input_data_filename})` : 'Base model package input_data.json'}
                </p>
                {cr.what_must_stay_the_same ? <p className="text-sm text-[var(--muted)]">Keep the same: {cr.what_must_stay_the_same}</p> : null}
              </Card>
            ))
          ) : (
            <Card className="rounded-[1.7rem]">
              <p className="text-sm text-[var(--muted)]">No change requests yet.</p>
            </Card>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Run history</p>
            <h2 className="mt-2 text-3xl">Workflow runs</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {runsQuery.data?.length ?? 0} run{(runsQuery.data?.length ?? 0) === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <div className="grid gap-4">
          {runsQuery.data?.length ? (
            runsQuery.data.map((run) => (
              <Card key={run.id} className="rounded-[1.7rem]">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <Link href={`/projects/${params.id}/runs/${run.id}`} className="text-lg font-semibold text-[var(--ink)] no-underline hover:text-[var(--accent-strong)]">
                      {run.change_request_summary || 'Workflow run'}
                    </Link>
                    <p className="mt-2 text-sm text-[var(--muted)]">Base model: {run.model_package_filename || 'Unknown package'}</p>
                  </div>
                  <Badge tone={run.status === 'completed' ? 'success' : run.status === 'needs_review' ? 'warning' : run.status === 'failed' ? 'danger' : 'default'}>
                    {run.status}
                  </Badge>
                </div>
                <p className="text-sm text-[var(--muted)]">
                  Runtime input: {run.runtime_input_source === 'change_request_override' ? 'Change request override' : 'Base model package input'}
                </p>
                <p className="text-sm text-[var(--muted)]">Model: {run.model_provider} · {run.model_name} · {run.model_preset}</p>
              </Card>
            ))
          ) : (
            <Card className="rounded-[1.7rem]">
              <p className="text-sm text-[var(--muted)]">No workflow runs yet.</p>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
}
