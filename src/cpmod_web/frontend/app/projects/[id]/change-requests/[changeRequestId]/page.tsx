'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api';

export default function ChangeRequestDetailPage({
  params,
}: {
  params: { id: string; changeRequestId: string };
}) {
  const router = useRouter();
  const crQuery = useQuery({
    queryKey: ['change-request', params.changeRequestId],
    queryFn: () => api.getChangeRequest(params.changeRequestId),
  });
  const runsQuery = useQuery({
    queryKey: ['project-runs', params.id],
    queryFn: () => api.listProjectRuns(params.id),
  });

  if (crQuery.isLoading) return <p>Loading change request…</p>;
  if (crQuery.error || !crQuery.data) return <p>Unable to load change request.</p>;

  const changeRequest = crQuery.data;
  const linkedRuns = (runsQuery.data ?? []).filter((run) => run.change_request_id === changeRequest.id);

  async function handleDelete() {
    if (!window.confirm('Delete this change request and its linked runs?')) {
      return;
    }
    await api.deleteChangeRequest(changeRequest.id);
    router.push(`/projects/${params.id}`);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Change request</h1>
          <p className="mt-2 text-sm text-slate-600">
            Base model:{' '}
            {changeRequest.model_package_id ? (
              <Link href={`/projects/${params.id}/model-packages/${changeRequest.model_package_id}`} className="underline">
                {changeRequest.model_package_filename || 'View model package'}
              </Link>
            ) : (
              changeRequest.model_package_filename || 'Unknown package'
            )}
          </p>
        </div>
        <Button type="button" className="bg-rose-700 hover:bg-rose-800" onClick={handleDelete}>
          Delete change request
        </Button>
      </div>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Requested change</h2>
        <p className="whitespace-pre-wrap text-sm text-slate-800">{changeRequest.what_should_change}</p>
        {changeRequest.what_must_stay_the_same ? (
          <>
            <h3 className="text-sm font-semibold text-slate-900">Must stay the same</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-700">{changeRequest.what_must_stay_the_same}</p>
          </>
        ) : null}
        {changeRequest.additional_detail ? (
          <>
            <h3 className="text-sm font-semibold text-slate-900">Additional context</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-700">{changeRequest.additional_detail}</p>
          </>
        ) : null}
        <h3 className="text-sm font-semibold text-slate-900">Runtime input</h3>
        <p className="text-sm text-slate-700">
          {changeRequest.override_input_data_filename
            ? `This change request uses override input_data.json: ${changeRequest.override_input_data_filename}.`
            : 'This change request uses the base model package input_data.json.'}
        </p>
        {changeRequest.override_input_data_file_url ? (
          <a href={changeRequest.override_input_data_file_url} target="_blank" className="text-sm text-blue-700 underline">
            Download override input_data.json
          </a>
        ) : null}
        {changeRequest.override_input_value_info ? (
          <>
            <h3 className="text-sm font-semibold text-slate-900">Override input notes</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-700">{changeRequest.override_input_value_info}</p>
          </>
        ) : null}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Runs from this change request</h2>
        {linkedRuns.length ? (
          <div className="grid gap-3">
            {linkedRuns.map((run) => (
              <div key={run.id} className="rounded-lg border border-slate-200 p-3">
                <Link href={`/projects/${params.id}/runs/${run.id}`} className="font-medium">
                  View run
                </Link>
                <p className="mt-1 text-sm text-slate-600">Status: {run.status}</p>
                <p className="text-sm text-slate-600">
                  Runtime input: {run.runtime_input_source === 'change_request_override' ? 'Change request override' : 'Base model package input'}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-600">No runs yet.</p>
        )}
      </Card>
    </div>
  );
}
