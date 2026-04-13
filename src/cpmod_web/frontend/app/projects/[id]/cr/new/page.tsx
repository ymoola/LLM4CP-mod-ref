'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { ChangeRequestForm } from '@/components/cr-form';

export default function NewChangeRequestPage({ params }: { params: { id: string } }) {
  const packagesQuery = useQuery({ queryKey: ['model-packages', params.id], queryFn: () => api.listModelPackages(params.id) });
  const validatedPackages = (packagesQuery.data ?? []).filter((pkg) => pkg.validation_status === 'validated');

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">New change request</h1>
      <p className="max-w-2xl text-sm text-slate-600">
        Describe the requested change in plain language, then choose which validated base model package it should apply to.
      </p>
      {validatedPackages.length > 0 ? (
        <ChangeRequestForm projectId={params.id} modelPackages={validatedPackages} />
      ) : (
        <p className="text-sm text-slate-600">Upload and validate a model package before creating a change request.</p>
      )}
    </div>
  );
}
