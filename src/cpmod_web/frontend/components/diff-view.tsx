export function DiffView({ diffUrl }: { diffUrl: string | null }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
      {diffUrl ? (
        <a href={diffUrl} target="_blank" rel="noreferrer">
          Open unified diff artifact
        </a>
      ) : (
        <p className="text-slate-600">No diff artifact available yet.</p>
      )}
    </div>
  );
}
