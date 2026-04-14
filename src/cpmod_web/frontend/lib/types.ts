export type RunStatus = 'pending' | 'in_progress' | 'awaiting_clarification' | 'completed' | 'needs_review' | 'failed';
export type ModelPreset = 'fast' | 'quality';
export type Provider = 'openai' | 'openrouter';

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
}

export interface ModelPackage {
  id: string;
  project_id: string;
  filename: string;
  problem_description_filename: string;
  input_data_filename: string;
  validation_status: string;
  validation_summary?: string | null;
  metadata: Record<string, unknown>;
  parser_output?: Record<string, unknown> | null;
  created_at?: string | null;
  model_file_url?: string | null;
  problem_description_file_url?: string | null;
  input_data_file_url?: string | null;
  validation_log_url?: string | null;
}

export interface ChangeRequest {
  id: string;
  project_id: string;
  model_package_id: string;
  model_package_filename?: string | null;
  override_input_data_filename?: string | null;
  override_input_data_file_url?: string | null;
  override_input_value_info?: string | null;
  what_should_change: string;
  what_must_stay_the_same?: string | null;
  objective_change: 'yes' | 'no' | 'unsure';
  expected_output_changes?: string | null;
  additional_detail?: string | null;
  status: string;
  created_at?: string | null;
}

export interface ModelCatalogEntry {
  id: string;
  preset: ModelPreset;
  provider: Provider;
  model_name: string;
  label: string;
  description: string;
  reasoning_effort?: 'none' | 'minimal' | 'low' | 'medium' | 'high' | null;
  max_output_tokens?: number | null;
  is_default: boolean;
}

export interface ProviderCredentialStatus {
  provider: Provider;
  has_key: boolean;
  updated_at?: string | null;
}

export interface RunEvent {
  id: string;
  run_id: string;
  stage: string;
  outcome: string;
  failure_type?: string | null;
  message?: string | null;
  attempt: number;
  payload: Record<string, unknown>;
  created_at?: string | null;
}

export interface RunArtifact {
  id: string;
  run_id: string;
  type: string;
  storage_path?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  signed_url?: string | null;
}

export interface WorkflowRun {
  id: string;
  change_request_id: string;
  project_id?: string | null;
  model_package_id?: string | null;
  model_package_filename?: string | null;
  change_request_summary?: string | null;
  runtime_input_source?: 'base' | 'change_request_override' | null;
  runtime_input_filename?: string | null;
  runtime_input_file_url?: string | null;
  status: RunStatus;
  model_preset: ModelPreset;
  model_provider: Provider;
  model_name: string;
  api_key_provider: Provider;
  credential_source: 'user_saved';
  clarification_questions: string[];
  clarification_answers: string[];
  invariants?: Record<string, unknown> | null;
  change_summary?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failure_type?: string | null;
  last_error?: string | null;
  created_at?: string | null;
  events: RunEvent[];
  artifacts: RunArtifact[];
}

export interface WorkflowRunSummary {
  id: string;
  change_request_id: string;
  project_id?: string | null;
  model_package_id?: string | null;
  model_package_filename?: string | null;
  change_request_summary?: string | null;
  runtime_input_source?: 'base' | 'change_request_override' | null;
  status: RunStatus;
  model_preset: ModelPreset;
  model_provider: Provider;
  model_name: string;
  api_key_provider: Provider;
  credential_source: 'user_saved';
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failure_type?: string | null;
}

export interface RunCreatePayload {
  change_request_id: string;
  model_preset: ModelPreset;
  model_provider: Provider;
  model_name: string;
  api_key_provider: Provider;
}

export interface DashboardCounts {
  total_projects: number;
  validated_model_packages: number;
  completed_runs: number;
  runs_needing_review: number;
  failed_runs: number;
}

export interface DashboardOverview {
  counts: DashboardCounts;
  recent_projects: Project[];
  recent_runs: WorkflowRunSummary[];
  runs_awaiting_clarification: WorkflowRunSummary[];
  runs_needing_review: WorkflowRunSummary[];
}
