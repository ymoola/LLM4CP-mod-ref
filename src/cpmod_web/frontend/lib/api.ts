import type {
  ChangeRequest,
  DashboardOverview,
  ModelCatalogEntry,
  ModelPackage,
  Project,
  Provider,
  ProviderCredentialStatus,
  RunCreatePayload,
  WorkflowRun,
  WorkflowRunSummary,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function authHeaders(): Promise<Record<string, string>> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cpmod-access-token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders();
  const mergedHeaders: Record<string, string> = {
    ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...headers,
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: mergedHeaders,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json();
}

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const headers = await authHeaders();
  const mergedHeaders: Record<string, string> = {
    ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...headers,
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: mergedHeaders,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
}

async function readError(response: Response): Promise<string> {
  const raw = await response.text();
  if (!raw) return `Request failed with status ${response.status}.`;
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    if (parsed.detail) return parsed.detail;
  } catch {
    // Fall back to the raw response body.
  }
  return raw;
}

export const api = {
  getDashboardOverview: () => request<DashboardOverview>('/dashboard/overview'),
  listProjects: () => request<Project[]>('/projects'),
  createProject: (payload: { name: string; description?: string }) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  deleteProject: (projectId: string) => requestVoid(`/projects/${projectId}`, { method: 'DELETE' }),
  listProjectRuns: (projectId: string) => request<WorkflowRunSummary[]>(`/projects/${projectId}/runs`),
  listModelPackages: (projectId: string) => request<ModelPackage[]>(`/projects/${projectId}/model-packages`),
  getModelPackage: (id: string) => request<ModelPackage>(`/model-packages/${id}`),
  uploadModelPackage: (projectId: string, formData: FormData) => request<ModelPackage>(`/projects/${projectId}/model-packages`, { method: 'POST', body: formData }),
  deleteModelPackage: (id: string) => requestVoid(`/model-packages/${id}`, { method: 'DELETE' }),
  listChangeRequests: (projectId: string) => request<ChangeRequest[]>(`/projects/${projectId}/change-requests`),
  getChangeRequest: (id: string) => request<ChangeRequest>(`/change-requests/${id}`),
  createChangeRequest: (projectId: string, formData: FormData) => request<ChangeRequest>(`/projects/${projectId}/change-requests`, { method: 'POST', body: formData }),
  deleteChangeRequest: (id: string) => requestVoid(`/change-requests/${id}`, { method: 'DELETE' }),
  createRun: (payload: RunCreatePayload) => request<WorkflowRun>('/runs', { method: 'POST', body: JSON.stringify(payload) }),
  getRun: (runId: string) => request<WorkflowRun>(`/runs/${runId}`),
  submitClarification: (runId: string, answers: string[]) => request<WorkflowRun>(`/runs/${runId}/clarify`, { method: 'POST', body: JSON.stringify({ answers }) }),
  listModelCatalog: () => request<ModelCatalogEntry[]>('/settings/model-catalog'),
  listProviderCredentials: () => request<ProviderCredentialStatus[]>('/settings/credentials'),
  saveProviderCredential: (provider: Provider, apiKey: string) =>
    request<ProviderCredentialStatus>(`/settings/credentials/${provider}`, { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }),
  deleteProviderCredential: (provider: Provider) => requestVoid(`/settings/credentials/${provider}`, { method: 'DELETE' }),
};
