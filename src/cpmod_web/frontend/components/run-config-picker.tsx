'use client';

import { useMemo } from 'react';

import type { ModelCatalogEntry, ProviderCredentialStatus, RunCreatePayload } from '../lib/types';
import { Badge } from './ui/badge';
import { Select } from './ui/select';

function sortEntries(catalog: ModelCatalogEntry[]) {
  return [...catalog].sort((left, right) => {
    if (left.preset !== right.preset) return left.preset.localeCompare(right.preset);
    if (left.provider !== right.provider) return left.provider.localeCompare(right.provider);
    return left.label.localeCompare(right.label);
  });
}

export function getDefaultRunConfig(catalog: ModelCatalogEntry[], preferredPreset: 'fast' | 'quality' = 'fast'): RunCreatePayload | null {
  const ordered = sortEntries(catalog);
  const preferred = ordered.find((entry) => entry.preset === preferredPreset && entry.is_default)
    ?? ordered.find((entry) => entry.preset === preferredPreset)
    ?? ordered.find((entry) => entry.is_default)
    ?? ordered[0];
  if (!preferred) return null;
  return {
    change_request_id: '',
    model_preset: preferred.preset,
    model_provider: preferred.provider,
    model_name: preferred.model_name,
    api_key_provider: preferred.provider,
  };
}

export function normalizeRunConfig(current: RunCreatePayload | null, catalog: ModelCatalogEntry[]): RunCreatePayload | null {
  if (!catalog.length) return null;
  if (!current) return getDefaultRunConfig(catalog);
  const directMatch = catalog.find(
    (entry) => entry.preset === current.model_preset && entry.provider === current.model_provider && entry.model_name === current.model_name,
  );
  if (directMatch) {
    return {
      ...current,
      api_key_provider: current.model_provider,
    };
  }
  const nextMatch = catalog.find((entry) => entry.preset === current.model_preset && entry.is_default)
    ?? catalog.find((entry) => entry.preset === current.model_preset)
    ?? catalog[0];
  return {
    change_request_id: current.change_request_id,
    model_preset: nextMatch.preset,
    model_provider: nextMatch.provider,
    model_name: nextMatch.model_name,
    api_key_provider: nextMatch.provider,
  };
}

export function RunConfigPicker({
  value,
  onChange,
  catalog,
  credentialStatuses,
  disabled = false,
}: {
  value: RunCreatePayload | null;
  onChange: (next: RunCreatePayload) => void;
  catalog: ModelCatalogEntry[];
  credentialStatuses: ProviderCredentialStatus[];
  disabled?: boolean;
}) {
  const selected = useMemo(() => normalizeRunConfig(value, catalog), [value, catalog]);
  const modelsForPreset = useMemo(
    () => catalog.filter((entry) => entry.preset === (selected?.model_preset ?? 'fast')),
    [catalog, selected?.model_preset],
  );
  const credentialLookup = useMemo(
    () => new Map(credentialStatuses.map((status) => [status.provider, status])),
    [credentialStatuses],
  );

  if (!selected) {
    return <p className="text-sm text-[var(--muted)]">No curated models are available yet.</p>;
  }

  const activeCredential = credentialLookup.get(selected.api_key_provider);
  const hasCredential = Boolean(activeCredential?.has_key);
  const checkingCredentials = credentialStatuses.length === 0;

  return (
    <div className="space-y-4 rounded-[1.5rem] border border-[var(--line)] bg-[rgba(255,252,246,0.78)] p-4 shadow-[var(--shadow)]">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--ink)]">Run model selection</h3>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Choose a preset first, then pick one curated model inside that preset. The run will use your saved key for the selected provider.
        </p>
      </div>

      <div className="grid gap-2">
        <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Preset</label>
        <Select
          value={selected.model_preset}
          disabled={disabled}
          onChange={(event) => {
            const nextPreset = event.target.value as 'fast' | 'quality';
            const nextEntry = catalog.find((entry) => entry.preset === nextPreset && entry.is_default)
              ?? catalog.find((entry) => entry.preset === nextPreset);
            if (!nextEntry) return;
            onChange({
              ...selected,
              model_preset: nextEntry.preset,
              model_provider: nextEntry.provider,
              model_name: nextEntry.model_name,
              api_key_provider: nextEntry.provider,
            });
          }}
        >
          <option value="fast">Fast</option>
          <option value="quality">Quality</option>
        </Select>
      </div>

      <div className="grid gap-2">
        <label className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Model</label>
        <Select
          value={`${selected.model_provider}::${selected.model_name}`}
          disabled={disabled}
          onChange={(event) => {
            const [provider, modelName] = event.target.value.split('::');
            const nextEntry = modelsForPreset.find((entry) => entry.provider === provider && entry.model_name === modelName);
            if (!nextEntry) return;
            onChange({
              ...selected,
              model_preset: nextEntry.preset,
              model_provider: nextEntry.provider,
              model_name: nextEntry.model_name,
              api_key_provider: nextEntry.provider,
            });
          }}
        >
          {modelsForPreset.map((entry) => (
            <option key={entry.id} value={`${entry.provider}::${entry.model_name}`}>
              {entry.label} · {entry.provider}
            </option>
          ))}
        </Select>
        {modelsForPreset.length ? (
          <div className="rounded-[1.2rem] border border-[var(--line)] bg-[rgba(255,255,255,0.78)] p-3 text-sm text-[var(--ink)]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">
                {modelsForPreset.find((entry) => entry.provider === selected.model_provider && entry.model_name === selected.model_name)?.label ?? selected.model_name}
              </span>
              <Badge tone={selected.model_preset === 'quality' ? 'warning' : 'default'}>{selected.model_preset}</Badge>
              <Badge tone={checkingCredentials ? 'default' : hasCredential ? 'success' : 'danger'}>
                {checkingCredentials ? 'Checking saved key' : hasCredential ? `Saved ${selected.api_key_provider} key` : `Missing ${selected.api_key_provider} key`}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {modelsForPreset.find((entry) => entry.provider === selected.model_provider && entry.model_name === selected.model_name)?.description}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
