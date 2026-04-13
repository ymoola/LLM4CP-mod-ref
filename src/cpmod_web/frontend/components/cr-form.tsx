'use client';

import { useMemo, useState } from 'react';

import { api } from '@/lib/api';
import type { ModelPackage } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export function ChangeRequestForm({
  projectId,
  modelPackages,
}: {
  projectId: string;
  modelPackages: ModelPackage[];
}) {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const defaultPackageId = modelPackages[0]?.id ?? '';
  const [selectedPackageId, setSelectedPackageId] = useState(defaultPackageId);

  const selectedPackage = useMemo(
    () => modelPackages.find((pkg) => pkg.id === selectedPackageId) ?? null,
    [modelPackages, selectedPackageId],
  );
  const formatPackageLabel = (pkg: ModelPackage) => {
    const created = pkg.created_at ? new Date(pkg.created_at).toLocaleString() : null;
    const suffix = created ? `uploaded ${created}` : `id ${pkg.id.slice(0, 8)}`;
    return `${pkg.filename} · ${suffix}`;
  };

  return (
    <form
      className="space-y-5"
      action={async (fd) => {
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
          const run = await api.createRun({ change_request_id: changeRequest.id, model_config: 'fast' });
          window.location.href = `/projects/${projectId}/runs/${run.id}`;
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unable to submit change request.');
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="grid gap-2">
          <label className="text-sm font-medium">Base model package</label>
          <select
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
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
          </select>
          {selectedPackage ? (
            <p className="text-xs text-slate-600">
              This change request and all runs from it will use <span className="font-medium">{formatPackageLabel(selectedPackage)}</span>.
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid gap-2">
        <label className="text-sm font-medium">Describe the change that needs to be made</label>
        <Textarea
          name="what_should_change"
          required
          placeholder="Explain the requested model change in plain language. You do not need CSP/COP terminology."
        />
      </div>

      <div className="grid gap-2">
        <label className="text-sm font-medium">Anything that must stay the same? (optional)</label>
        <Textarea
          name="what_must_stay_the_same"
          placeholder="Optional: mention any logic, outputs, or variable names that should remain unchanged."
        />
      </div>

      <details className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-900">Extra context (optional)</summary>
        <div className="mt-4 grid gap-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Additional context for the workflow</label>
            <Textarea
              name="additional_detail"
              placeholder="Optional: examples, edge cases, business rules, or anything else helpful."
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Override input_data.json (optional)</label>
            <Input name="override_input_data_file" type="file" accept=".json,application/json" />
            <p className="text-xs text-slate-600">
              If provided, this fully replaces the model package input for every run created from this change request.
            </p>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Override input notes (optional)</label>
            <Textarea
              name="override_input_value_info"
              placeholder='Only fill this in if the override adds fields, removes fields, renames fields, or changes what they mean. Example: "capacity" is now per-facility, and "facility_limits" is a new list aligned by facility index.'
            />
            <p className="text-xs text-slate-600">
              Base package input notes still remain the default. These notes only clarify how the override input should be interpreted for this change request.
            </p>
          </div>
        </div>
      </details>

      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="submit" disabled={submitting || !selectedPackageId}>
        {submitting ? 'Submitting…' : 'Run workflow'}
      </Button>
    </form>
  );
}
