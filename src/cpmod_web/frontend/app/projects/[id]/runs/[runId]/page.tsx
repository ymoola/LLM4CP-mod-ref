import { RunViewer } from '@/components/run-viewer';

export default function RunDetailPage({ params }: { params: { id: string; runId: string } }) {
  return <RunViewer runId={params.runId} />;
}
