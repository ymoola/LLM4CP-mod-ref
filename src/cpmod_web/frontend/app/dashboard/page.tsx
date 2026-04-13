import Link from 'next/link';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Dashboard</h1>
      <div className="flex gap-4">
        <Link href="/projects">Projects</Link>
        <Link href="/projects/new">Create project</Link>
      </div>
    </div>
  );
}
