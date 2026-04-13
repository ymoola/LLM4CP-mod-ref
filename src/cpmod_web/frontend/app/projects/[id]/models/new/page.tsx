import { ModelUploadForm } from '@/components/model-upload';

export default function NewModelPackagePage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Upload model package</h1>
      <ModelUploadForm projectId={params.id} />
    </div>
  );
}
