'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { WorkflowRun } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { ClarificationPanel } from '@/components/clarification-panel';
import { DiffView } from '@/components/diff-view';
import { InvariantsPanel } from '@/components/invariants-panel';

export function RunViewer({ runId }: { runId: string }) {
  const query = useQuery<WorkflowRun>({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'completed' || status === 'failed' || status === 'needs_review' ? false : 2500;
    },
  });

  if (query.isLoading) return <p>Loading run…</p>;
  if (query.error || !query.data) return <p>Unable to load run.</p>;

  const run = query.data;
  const diffArtifact = run.artifacts.find((artifact) => artifact.type === 'diff');
  const generatedModel = run.artifacts.find((artifact) => artifact.type === 'generated_model');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Workflow run</h1>
        <Badge tone={run.status === 'completed' ? 'success' : run.status === 'needs_review' ? 'warning' : run.status === 'failed' ? 'danger' : 'default'}>{run.status}</Badge>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-2 text-lg font-semibold">Run context</h2>
        {run.model_package_filename ? <p className="text-sm text-slate-700">Base model package: {run.model_package_filename}</p> : null}
        {run.change_request_summary ? <p className="mt-2 text-sm text-slate-700">Requested change: {run.change_request_summary}</p> : null}
        <p className="mt-2 text-sm text-slate-700">
          Selected model: {run.model_provider} · {run.model_name} · {run.model_preset}
        </p>
        <p className="text-sm text-slate-700">Credential source: saved {run.api_key_provider} key</p>
        <p className="mt-2 text-sm text-slate-700">
          Runtime input source: {run.runtime_input_source === 'change_request_override' ? 'Change request override input_data.json' : 'Base model package input_data.json'}
        </p>
        {run.runtime_input_filename ? (
          <p className="text-sm text-slate-700">
            Runtime input file: {run.runtime_input_file_url ? <a href={run.runtime_input_file_url} target="_blank">{run.runtime_input_filename}</a> : run.runtime_input_filename}
          </p>
        ) : null}
      </section>

      {run.status === 'awaiting_clarification' ? <ClarificationPanel run={run} /> : null}

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 text-lg font-semibold">Stage timeline</h2>
        <div className="space-y-3">
          {run.events.map((event) => (
            <div key={event.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center gap-3">
                <p className="font-medium capitalize">{event.stage.replaceAll('_', ' ')}</p>
                <Badge tone={event.outcome === 'succeeded' ? 'success' : event.outcome === 'failed' ? 'danger' : event.outcome === 'waiting' ? 'warning' : 'default'}>{event.outcome}</Badge>
                <span className="text-xs text-slate-500">Attempt {event.attempt}</span>
              </div>
              {event.message ? <p className="mt-2 text-sm text-slate-700">{event.message}</p> : null}
            </div>
          ))}
        </div>
      </section>

      <InvariantsPanel invariants={run.invariants} summary={run.change_summary} />

      <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Artifacts</h2>
        {generatedModel?.signed_url ? <a href={generatedModel.signed_url} target="_blank">Download generated model</a> : <p className="text-sm text-slate-500">Generated model not available yet.</p>}
        {run.artifacts.length ? (
          <div className="grid gap-2 text-sm">
            {run.artifacts.map((artifact) => (
              artifact.signed_url ? (
                <a key={artifact.id} href={artifact.signed_url} target="_blank">
                  {artifact.type.replaceAll('_', ' ')}
                </a>
              ) : (
                <p key={artifact.id} className="text-slate-500">{artifact.type.replaceAll('_', ' ')}</p>
              )
            ))}
          </div>
        ) : null}
        <DiffView diffUrl={diffArtifact?.signed_url ?? null} />
      </section>

      {run.last_error ? (
        <section className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          <h2 className="font-semibold">Last error</h2>
          <p>{run.last_error}</p>
        </section>
      ) : null}
    </div>
  );
}
