'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { ModelPackage, RunCreatePayload } from '../lib/types';
import { getDefaultRunConfig, normalizeRunConfig, RunConfigPicker } from './run-config-picker';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select } from './ui/select';
import { Textarea } from './ui/textarea';

export function ChangeRequestForm({
  projectId,
  modelPackages,
}: {
  projectId: string;
  modelPackages: ModelPackage[];
}) {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [runConfig, setRunConfig] = useState<RunCreatePayload | null>(null);
  const defaultPackageId = modelPackages[0]?.id ?? '';
  const [selectedPackageId, setSelectedPackageId] = useState(defaultPackageId);
  const catalogQuery = useQuery({ queryKey: ['model-catalog'], queryFn: () => api.listModelCatalog() });
  const credentialQuery = useQuery({ queryKey: ['provider-credentials'], queryFn: () => api.listProviderCredentials() });

  const selectedPackage = useMemo(
    () => modelPackages.find((pkg) => pkg.id === selectedPackageId) ?? null,
    [modelPackages, selectedPackageId],
  );
  const missingProviderKey = useMemo(() => {
    if (!runConfig) return null;
    if (!credentialQuery.data) return null;
    const status = (credentialQuery.data ?? []).find((item) => item.provider === runConfig.api_key_provider);
    return status?.has_key ? null : runConfig.api_key_provider;
  }, [credentialQuery.data, runConfig]);

  useEffect(() => {
    const catalog = catalogQuery.data ?? [];
    if (!catalog.length) return;
    setRunConfig((current) => normalizeRunConfig(current, catalog) ?? getDefaultRunConfig(catalog));
  }, [catalogQuery.data]);

  const formatPackageLabel = (pkg: ModelPackage) => {
    const created = pkg.created_at ? new Date(pkg.created_at).toLocaleString() : null;
    const suffix = created ? `uploaded ${created}` : `id ${pkg.id.slice(0, 8)}`;
    return `${pkg.filename} · ${suffix}`;
  };

  return (
    <form
      className="space-y-5"
      action={async (fd) => {
        if (!runConfig) {
          setError('Choose a run model before starting the workflow.');
          return;
        }
        if (missingProviderKey) {
          setError(`Save an API key for ${missingProviderKey} in Settings before running the workflow.`);
          return;
        }
        setSubmitting(true);
        setError(null);
        try {
          const formData = new FormData();
          formData.set('model_package_id', String(fd.get('model_package_id') || '').trim());
          formData.set('what_should_change', String(fd.get('what_should_change') || '').trim());
          const mustStay = String(fd.get('what_must_stay_the_same') || '').trim();
          if (mustStay) {
            formData.set('what_must_stay_the_same', mustStay);
          }
          const extraDetail = String(fd.get('additional_detail') || '').trim();
          if (extraDetail) {
            formData.set('additional_detail', extraDetail);
          }
          const overrideFile = fd.get('override_input_data_file');
          if (overrideFile instanceof File && overrideFile.size > 0) {
            formData.set('override_input_data_file', overrideFile);
          }
          const overrideNotes = String(fd.get('override_input_value_info') || '').trim();
          if (overrideNotes) {
            formData.set('override_input_value_info', overrideNotes);
          }

          const changeRequest = await api.createChangeRequest(projectId, formData);
          const run = await api.createRun({ ...runConfig, change_request_id: changeRequest.id });
          window.location.href = `/projects/${projectId}/runs/${run.id}`;
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unable to submit change request.');
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <div className="rounded-[1.5rem] border border-[var(--line)] bg-[rgba(255,252,246,0.78)] p-4 shadow-[var(--shadow)]">
        <div className="grid gap-2">
          <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Base model package</label>
          <Select
            name="model_package_id"
            value={selectedPackageId}
            onChange={(event) => setSelectedPackageId(event.target.value)}
            required
          >
            {modelPackages.map((pkg) => (
              <option key={pkg.id} value={pkg.id}>
                {formatPackageLabel(pkg)}
              </option>
            ))}
          </Select>
          {selectedPackage ? (
            <p className="text-xs text-[var(--muted)]">
              This change request and all runs from it will use <span className="font-medium">{formatPackageLabel(selectedPackage)}</span>.
            </p>
          ) : null}
        </div>
      </div>

      <RunConfigPicker
        value={runConfig}
        onChange={setRunConfig}
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
          before launching the workflow.
        </p>
      ) : null}

      <div className="grid gap-2">
        <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Describe the change that needs to be made</label>
        <Textarea
          name="what_should_change"
          required
          placeholder="Explain the requested model change in plain language. You do not need CSP/COP terminology."
        />
      </div>

      <div className="grid gap-2">
        <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Anything that must stay the same? (optional)</label>
        <Textarea
          name="what_must_stay_the_same"
          placeholder="Optional: mention any logic, outputs, or variable names that should remain unchanged."
        />
      </div>

      <details className="rounded-[1.5rem] border border-[var(--line)] bg-[rgba(255,252,246,0.78)] p-4 shadow-[var(--shadow)]">
        <summary className="cursor-pointer text-sm font-semibold uppercase tracking-[0.12em] text-[var(--ink)]">Extra context (optional)</summary>
        <div className="mt-4 grid gap-4">
          <div className="grid gap-2">
            <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Additional context for the workflow</label>
            <Textarea
              name="additional_detail"
              placeholder="Optional: examples, edge cases, business rules, or anything else helpful."
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Override input_data.json (optional)</label>
            <Input name="override_input_data_file" type="file" accept=".json,application/json" />
            <p className="text-xs text-[var(--muted)]">
              If provided, this fully replaces the model package input for every run created from this change request.
            </p>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Override input notes (optional)</label>
            <Textarea
              name="override_input_value_info"
              placeholder='Only fill this in if the override adds fields, removes fields, renames fields, or changes what they mean. Example: "capacity" is now per-facility, and "facility_limits" is a new list aligned by facility index.'
            />
            <p className="text-xs text-[var(--muted)]">
              Base package input notes still remain the default. These notes only clarify how the override input should be interpreted for this change request.
            </p>
          </div>
        </div>
      </details>

      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button
        type="submit"
        disabled={submitting || !selectedPackageId || !runConfig || Boolean(missingProviderKey) || catalogQuery.isLoading || credentialQuery.isLoading}
      >
        {submitting ? 'Submitting…' : 'Run workflow'}
      </Button>
    </form>
  );
}
