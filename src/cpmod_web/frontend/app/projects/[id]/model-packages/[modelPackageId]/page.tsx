'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api';

export default function ModelPackageDetailPage({
  params,
}: {
  params: { id: string; modelPackageId: string };
}) {
  const router = useRouter();
  const query = useQuery({
    queryKey: ['model-package', params.modelPackageId],
    queryFn: () => api.getModelPackage(params.modelPackageId),
  });

  if (query.isLoading) return <p>Loading model package…</p>;
  if (query.error || !query.data) return <p>Unable to load model package.</p>;

  const pkg = query.data;

  async function handleDelete() {
    if (!window.confirm(`Delete model package "${pkg.filename}"? This also removes linked change requests and runs.`)) {
      return;
    }
    await api.deleteModelPackage(pkg.id);
    router.push(`/projects/${params.id}`);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">{pkg.filename}</h1>
          <p className="mt-2 text-sm text-slate-600">Validation: {pkg.validation_status}</p>
        </div>
        <Button type="button" className="bg-rose-700 hover:bg-rose-800" onClick={handleDelete}>
          Delete model package
        </Button>
      </div>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Execution contract</h2>
        <p className="text-sm text-slate-700">Mode: {String(pkg.metadata.execution_mode || 'script')}</p>
        {pkg.metadata.entrypoint_name ? <p className="text-sm text-slate-700">Entrypoint: {String(pkg.metadata.entrypoint_name)}</p> : null}
        <p className="text-sm text-slate-700">
          Output variable names: {Array.isArray(pkg.metadata.output_variable_names) && pkg.metadata.output_variable_names.length ? pkg.metadata.output_variable_names.join(', ') : 'None'}
        </p>
        <p className="text-sm text-slate-700">
          Important names: {Array.isArray(pkg.metadata.key_names_to_preserve) && pkg.metadata.key_names_to_preserve.length ? pkg.metadata.key_names_to_preserve.join(', ') : 'None provided'}
        </p>
        <p className="text-sm text-slate-700 whitespace-pre-wrap">
          Input field guide: {String(pkg.metadata.input_value_info || 'No input field guide provided.')}
        </p>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Files</h2>
        <div className="grid gap-2 text-sm">
          {pkg.model_file_url ? <a href={pkg.model_file_url} target="_blank">Download base model</a> : null}
          {pkg.problem_description_file_url ? <a href={pkg.problem_description_file_url} target="_blank">Download problem description</a> : null}
          {pkg.input_data_file_url ? <a href={pkg.input_data_file_url} target="_blank">Download input data</a> : null}
          {pkg.validation_log_url ? <a href={pkg.validation_log_url} target="_blank">Download validation log</a> : null}
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Next steps</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <Link href={`/projects/${params.id}/cr/new`}>Create change request for this project</Link>
          <Link href={`/projects/${params.id}`}>Back to project</Link>
        </div>
      </Card>
    </div>
  );
}
