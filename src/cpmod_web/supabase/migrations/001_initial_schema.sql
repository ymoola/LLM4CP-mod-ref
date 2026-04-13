create extension if not exists pgcrypto;

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists model_packages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade not null,
  filename text not null,
  problem_description_filename text not null,
  input_data_filename text not null,
  model_storage_path text not null,
  problem_description_storage_path text not null,
  input_data_storage_path text not null,
  metadata jsonb not null default '{}'::jsonb,
  parser_output jsonb,
  validation_status text not null default 'pending',
  validation_summary text,
  created_at timestamptz not null default now(),
  constraint model_packages_validation_status_check check (validation_status in ('pending','running','validated','failed'))
);

create table if not exists change_requests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade not null,
  model_package_id uuid references model_packages(id) on delete cascade not null,
  what_should_change text not null,
  what_must_stay_the_same text not null,
  objective_change text not null default 'unsure',
  expected_output_changes text,
  additional_detail text,
  status text not null default 'submitted',
  created_at timestamptz not null default now(),
  constraint change_requests_objective_change_check check (objective_change in ('yes','no','unsure')),
  constraint change_requests_status_check check (status in ('draft','submitted'))
);

create table if not exists workflow_runs (
  id uuid primary key default gen_random_uuid(),
  change_request_id uuid references change_requests(id) on delete cascade not null,
  status text not null default 'pending',
  model_config text not null default 'quality',
  picked_at timestamptz,
  clarification_questions jsonb not null default '[]'::jsonb,
  clarification_answers jsonb not null default '[]'::jsonb,
  invariants jsonb,
  change_summary text,
  state_json jsonb,
  resume_from_stage text,
  started_at timestamptz,
  completed_at timestamptz,
  failure_type text,
  last_error text,
  created_at timestamptz not null default now(),
  constraint workflow_runs_status_check check (status in ('pending','in_progress','awaiting_clarification','completed','needs_review','failed')),
  constraint workflow_runs_model_config_check check (model_config in ('fast','quality'))
);

create table if not exists run_events (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references workflow_runs(id) on delete cascade not null,
  stage text not null,
  outcome text not null,
  failure_type text,
  message text,
  attempt integer not null default 1,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists run_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references workflow_runs(id) on delete cascade,
  type text not null,
  storage_path text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table projects enable row level security;
alter table model_packages enable row level security;
alter table change_requests enable row level security;
alter table workflow_runs enable row level security;
alter table run_events enable row level security;
alter table run_artifacts enable row level security;

drop policy if exists projects_owner_policy on projects;
create policy projects_owner_policy on projects
  for all using (auth.uid() = user_id);

drop policy if exists model_packages_owner_policy on model_packages;
create policy model_packages_owner_policy on model_packages
  for all using (
    project_id in (select id from projects where user_id = auth.uid())
  );

drop policy if exists change_requests_owner_policy on change_requests;
create policy change_requests_owner_policy on change_requests
  for all using (
    project_id in (select id from projects where user_id = auth.uid())
  );

drop policy if exists workflow_runs_owner_policy on workflow_runs;
create policy workflow_runs_owner_policy on workflow_runs
  for all using (
    change_request_id in (
      select id from change_requests where project_id in (
        select id from projects where user_id = auth.uid()
      )
    )
  );

drop policy if exists run_events_owner_policy on run_events;
create policy run_events_owner_policy on run_events
  for all using (
    run_id in (
      select id from workflow_runs where change_request_id in (
        select id from change_requests where project_id in (
          select id from projects where user_id = auth.uid()
        )
      )
    )
  );

drop policy if exists run_artifacts_owner_policy on run_artifacts;
create policy run_artifacts_owner_policy on run_artifacts
  for all using (
    run_id in (
      select id from workflow_runs where change_request_id in (
        select id from change_requests where project_id in (
          select id from projects where user_id = auth.uid()
        )
      )
    )
    or run_id is null
  );

create or replace function claim_pending_run()
returns setof workflow_runs
language sql
as $$
  update workflow_runs
  set status = 'in_progress', picked_at = now(), started_at = coalesce(started_at, now())
  where id = (
    select id from workflow_runs
    where status = 'pending'
    order by created_at asc
    limit 1
    for update skip locked
  )
  returning *;
$$;
