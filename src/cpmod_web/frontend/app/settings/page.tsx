'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { Provider } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

function ProviderKeyCard({ provider }: { provider: Provider }) {
  const credentialsQuery = useQuery({ queryKey: ['provider-credentials'], queryFn: () => api.listProviderCredentials() });
  const [apiKey, setApiKey] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = (credentialsQuery.data ?? []).find((entry) => entry.provider === provider);

  async function saveKey() {
    if (!apiKey.trim()) {
      setError('Enter a provider API key before saving.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.saveProviderCredential(provider, apiKey);
      setApiKey('');
      await credentialsQuery.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save provider key.');
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteKey() {
    if (!window.confirm(`Delete the saved ${provider} API key?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.deleteProviderCredential(provider);
      await credentialsQuery.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete provider key.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold capitalize">{provider}</h2>
          <p className="text-sm text-slate-600">Keys are encrypted server-side and are never shown again after save.</p>
        </div>
        <Badge tone={status?.has_key ? 'success' : 'warning'}>{status?.has_key ? 'Key saved' : 'No key saved'}</Badge>
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium">API key</label>
        <Input
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder={status?.has_key ? 'Enter a new key to replace the existing one' : 'Paste your provider API key'}
        />
        {status?.updated_at ? (
          <p className="text-xs text-slate-500">Last updated {new Date(status.updated_at).toLocaleString()}.</p>
        ) : null}
      </div>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={saveKey} disabled={submitting}>
          {submitting ? 'Saving…' : status?.has_key ? 'Replace key' : 'Save key'}
        </Button>
        {status?.has_key ? (
          <Button type="button" className="bg-rose-700 hover:bg-rose-800" onClick={deleteKey} disabled={submitting}>
            Delete key
          </Button>
        ) : null}
      </div>
    </Card>
  );
}

export default function SettingsPage() {
  const catalogQuery = useQuery({ queryKey: ['model-catalog'], queryFn: () => api.listModelCatalog() });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold">Settings</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Save provider keys once, then reuse them across runs. Model selection stays per run, but only curated models shown below can be launched.
        </p>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <ProviderKeyCard provider="openai" />
        <ProviderKeyCard provider="openrouter" />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">Curated run models</h2>
          <p className="mt-1 text-sm text-slate-600">These are the preset-specific models the product currently allows for workflow runs.</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {catalogQuery.data?.map((entry) => (
            <Card key={entry.id} className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-lg font-semibold">{entry.label}</span>
                <Badge tone={entry.preset === 'quality' ? 'warning' : 'default'}>{entry.preset}</Badge>
                <Badge tone="default">{entry.provider}</Badge>
                {entry.is_default ? <Badge tone="success">Default</Badge> : null}
              </div>
              <p className="text-sm text-slate-600">{entry.description}</p>
              <p className="text-xs text-slate-500">Model id: {entry.model_name}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
