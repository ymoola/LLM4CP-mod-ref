import { ModelUploadForm } from '../../../../../components/model-upload';

export default function NewModelPackagePage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-6">
      <div className="page-intro">
        <p className="eyebrow">Model package intake</p>
        <h1 className="text-4xl sm:text-5xl">Upload a validated base model</h1>
        <p>
          Bring in the CPMpy model file, the problem description, and the runtime input contract so the workflow can reason from a stable, executable starting point.
        </p>
      </div>
      <ModelUploadForm projectId={params.id} />
    </div>
  );
}
