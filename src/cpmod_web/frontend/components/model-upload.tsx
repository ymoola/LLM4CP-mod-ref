'use client';

import { useState } from 'react';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export function ModelUploadForm({ projectId }: { projectId: string }) {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [executionMode, setExecutionMode] = useState<'script' | 'build_model'>('build_model');

  async function onSubmit(formData: FormData) {
    setSubmitting(true);
    setError(null);
    try {
      await api.uploadModelPackage(projectId, formData);
      window.location.href = `/projects/${projectId}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="space-y-4"
      action={async (fd) => {
        await onSubmit(fd);
      }}
    >
      <div className="grid gap-2">
        <label className="text-sm font-medium">Base CPMpy model (.py)</label>
        <Input type="file" name="model_file" accept=".py" required />
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium">Problem description (.txt)</label>
        <Input type="file" name="description_file" accept=".txt" required />
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium">Input data (.json)</label>
        <Input type="file" name="input_data_file" accept="application/json,.json" required />
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium">Execution mode</label>
        <select
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          name="execution_mode"
          value={executionMode}
          onChange={(event) => setExecutionMode(event.target.value as 'script' | 'build_model')}
        >
          <option value="build_model">Module with build_model-style entrypoint</option>
          <option value="script">Standalone script that prints JSON</option>
        </select>
        <p className="text-xs text-slate-500">
          Choose <span className="font-medium">Module with build_model-style entrypoint</span> for thesis-style CPMpy files
          that return a model and variables. Choose <span className="font-medium">Standalone script</span> only if the
          file already runs by itself and prints JSON.
        </p>
      </div>
      {executionMode === 'build_model' ? (
        <>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Entrypoint function name</label>
            <Input name="entrypoint_name" defaultValue="build_model" required />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Returned output variable names</label>
            <Input
              name="output_variable_names"
              placeholder="sequence, setup"
              required
            />
            <p className="text-xs text-slate-500">
              List the returned values after the model, in order. Example: if the function returns
              <code className="mx-1 rounded bg-slate-100 px-1 py-0.5">model, sequence, setup</code>,
              enter <code className="mx-1 rounded bg-slate-100 px-1 py-0.5">sequence, setup</code>.
            </p>
          </div>
        </>
      ) : null}
      <div className="grid gap-2">
        <label className="text-sm font-medium">Important names to keep stable (optional)</label>
        <Input name="key_names_to_preserve" placeholder="sequence, setup, demand" />
        <p className="text-xs text-slate-500">
          Optional. Add variable names, input field names, or output keys that should not be renamed unless the change request explicitly asks for it.
        </p>
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium">Input field guide (optional but recommended)</label>
        <Textarea
          name="input_value_info"
          placeholder="Explain what the input_data.json fields mean, similar to value_info in desc.json."
        />
        <p className="text-xs text-slate-500">
          Example: describe what each input field represents so the workflow understands the semantics of the uploaded instance data.
        </p>
      </div>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? 'Uploading…' : 'Upload model package'}</Button>
    </form>
  );
}
