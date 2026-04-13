export function InvariantsPanel({ invariants, summary }: { invariants?: Record<string, unknown> | null; summary?: string | null }) {
  const data = invariants || {};
  const asList = (key: string) => ((data[key] as string[] | undefined) || []).join(', ') || '—';

  return (
    <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Change summary</h2>
      <p className="text-sm text-slate-700">{summary || 'No change summary available yet.'}</p>
      <dl className="grid gap-2 text-sm">
        <div><dt className="font-medium">Variables preserved</dt><dd>{asList('variables_preserved')}</dd></div>
        <div><dt className="font-medium">Variables added</dt><dd>{asList('variables_added')}</dd></div>
        <div><dt className="font-medium">Objective changed</dt><dd>{String(Boolean(data['objective_changed']))}</dd></div>
        <div><dt className="font-medium">Constraints added</dt><dd>{asList('constraints_added')}</dd></div>
        <div><dt className="font-medium">Constraints modified</dt><dd>{asList('constraints_modified')}</dd></div>
        <div><dt className="font-medium">Constraints removed</dt><dd>{asList('constraints_removed')}</dd></div>
      </dl>
    </div>
  );
}
