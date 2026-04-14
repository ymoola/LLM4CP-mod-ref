'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { RunCreatePayload } from '../lib/types';
import { getDefaultRunConfig, normalizeRunConfig, RunConfigPicker } from './run-config-picker';
import { Button } from './ui/button';

export function RunLauncher({ changeRequestId, projectId }: { changeRequestId: string; projectId: string }) {
  const [runConfig, setRunConfig] = useState<RunCreatePayload | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const catalogQuery = useQuery({ queryKey: ['model-catalog'], queryFn: () => api.listModelCatalog() });
  const credentialQuery = useQuery({ queryKey: ['provider-credentials'], queryFn: () => api.listProviderCredentials() });

  useEffect(() => {
    const catalog = catalogQuery.data ?? [];
    if (!catalog.length) return;
    setRunConfig((current) => {
      const next = normalizeRunConfig(current, catalog) ?? getDefaultRunConfig(catalog);
      return next ? { ...next, change_request_id: changeRequestId } : null;
    });
  }, [catalogQuery.data, changeRequestId]);

  const missingProviderKey = useMemo(() => {
    if (!runConfig) return null;
    if (!credentialQuery.data) return null;
    const statuses = credentialQuery.data ?? [];
    const status = statuses.find((item) => item.provider === runConfig.api_key_provider);
    return status?.has_key ? null : runConfig.api_key_provider;
  }, [credentialQuery.data, runConfig]);

  const ready = Boolean(runConfig && catalogQuery.data?.length && credentialQuery.data);

  async function handleCreateRun() {
    if (!runConfig) return;
    if (missingProviderKey) {
      setError(`Save an API key for ${missingProviderKey} before launching this run.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const run = await api.createRun(runConfig);
      window.location.href = `/projects/${projectId}/runs/${run.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create run.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <RunConfigPicker
        value={runConfig}
        onChange={(next) => setRunConfig({ ...next, change_request_id: changeRequestId })}
        catalog={catalogQuery.data ?? []}
        credentialStatuses={credentialQuery.data ?? []}
        disabled={submitting || catalogQuery.isLoading || credentialQuery.isLoading}
      />
      {missingProviderKey ? (
        <p className="text-sm text-amber-700">
          Save an API key for <span className="font-medium">{missingProviderKey}</span> in{' '}
          <Link href="/settings" className="underline">
            Settings
          </Link>{' '}
          before creating this run.
        </p>
      ) : null}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="button" onClick={handleCreateRun} disabled={!ready || submitting || Boolean(missingProviderKey)}>
        {submitting ? 'Launching…' : 'Create run from this change request'}
      </Button>
    </div>
  );
}
