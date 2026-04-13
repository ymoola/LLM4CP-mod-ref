'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

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
      <div className="flex flex-wrap items-center gap-4">
        <Link href={`/projects/${params.id}/models/new`}>Upload model package</Link>
        <Link href={`/projects/${params.id}/cr/new`}>New change request</Link>
        <Button
          type="button"
          className="bg-red-700 hover:bg-red-800"
          disabled={deleteProjectMutation.isPending}
          onClick={handleDeleteProject}
        >
          {deleteProjectMutation.isPending ? 'Deleting project…' : 'Delete project'}
        </Button>
        {deleteProjectMutation.isError ? (
          <p className="text-sm text-red-700">{deleteProjectMutation.error instanceof Error ? deleteProjectMutation.error.message : 'Unable to delete project.'}</p>
        ) : null}
      </div>
      <section className="space-y-3">
        <h2 className="text-2xl font-semibold">Model packages</h2>
        <div className="grid gap-4">
          {packagesQuery.data?.map((pkg) => (
            <Card key={pkg.id}>
              <Link href={`/projects/${params.id}/model-packages/${pkg.id}`} className="text-lg font-semibold">
                {pkg.filename}
              </Link>
              <p className="text-sm text-slate-600">Validation: {pkg.validation_status}</p>
              <p className="text-sm text-slate-600">
                Execution mode: {String(pkg.metadata.execution_mode || 'script')}
                {pkg.metadata.entrypoint_name ? ` · Entrypoint: ${String(pkg.metadata.entrypoint_name)}` : ''}
              </p>
              <p className="text-sm text-slate-600">{pkg.validation_summary || 'Awaiting validation summary.'}</p>
            </Card>
          ))}
        </div>
      </section>
      <section className="space-y-3">
        <h2 className="text-2xl font-semibold">Change requests</h2>
        <div className="grid gap-4">
          {crQuery.data?.map((cr) => (
            <Card key={cr.id}>
              <Link href={`/projects/${params.id}/change-requests/${cr.id}`} className="text-lg font-semibold">
                {cr.what_should_change}
              </Link>
              <p className="text-sm text-slate-600">
                Base model: {cr.model_package_filename || packageLookup.get(cr.model_package_id)?.filename || 'Unknown package'}
              </p>
              <p className="text-sm text-slate-600">
                Runtime input: {cr.override_input_data_filename ? `Override file (${cr.override_input_data_filename})` : 'Base model package input_data.json'}
              </p>
              {cr.what_must_stay_the_same ? <p className="text-sm text-slate-600">Keep the same: {cr.what_must_stay_the_same}</p> : null}
            </Card>
          ))}
        </div>
      </section>
      <section className="space-y-3">
        <h2 className="text-2xl font-semibold">Workflow runs</h2>
        <div className="grid gap-4">
          {runsQuery.data?.length ? (
            runsQuery.data.map((run) => (
              <Card key={run.id}>
              <Link href={`/projects/${params.id}/runs/${run.id}`} className="text-lg font-semibold">
                {run.change_request_summary || 'Workflow run'}
              </Link>
                <p className="text-sm text-slate-600">Base model: {run.model_package_filename || 'Unknown package'}</p>
                <p className="text-sm text-slate-600">
                  Runtime input: {run.runtime_input_source === 'change_request_override' ? 'Change request override' : 'Base model package input'}
                </p>
                <p className="text-sm text-slate-600">Model: {run.model_provider} · {run.model_name} · {run.model_preset}</p>
                <p className="text-sm text-slate-600">Status: {run.status}</p>
              </Card>
            ))
          ) : (
            <Card>
              <p className="text-sm text-slate-600">No workflow runs yet.</p>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
}
