alter table run_artifacts
  add column if not exists model_package_id uuid references model_packages(id) on delete cascade;

update run_artifacts
set model_package_id = nullif(metadata->>'model_package_id', '')::uuid
where model_package_id is null
  and metadata ? 'model_package_id';

create index if not exists run_artifacts_model_package_id_idx on run_artifacts(model_package_id);

alter table run_artifacts
  drop constraint if exists run_artifacts_owner_path_check;

alter table run_artifacts
  add constraint run_artifacts_owner_path_check check (
    run_id is not null or model_package_id is not null
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
    or model_package_id in (
      select id from model_packages where project_id in (
        select id from projects where user_id = auth.uid()
      )
    )
  );
