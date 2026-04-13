alter table workflow_runs
  add column if not exists model_preset text,
  add column if not exists model_provider text,
  add column if not exists model_name text,
  add column if not exists api_key_provider text;

update workflow_runs
set
  model_preset = coalesce(model_preset, model_config, 'quality'),
  model_provider = coalesce(
    model_provider,
    case coalesce(model_preset, model_config, 'quality')
      when 'fast' then 'openai'
      else 'openrouter'
    end
  ),
  model_name = coalesce(
    model_name,
    case coalesce(model_preset, model_config, 'quality')
      when 'fast' then 'gpt-5.4-mini'
      else 'anthropic/claude-opus-4.6'
    end
  ),
  api_key_provider = coalesce(
    api_key_provider,
    case coalesce(model_preset, model_config, 'quality')
      when 'fast' then 'openai'
      else 'openrouter'
    end
  )
where model_preset is null
   or model_provider is null
   or model_name is null
   or api_key_provider is null;

alter table workflow_runs
  alter column model_preset set default 'quality',
  alter column model_preset set not null,
  alter column model_provider set not null,
  alter column model_name set not null,
  alter column api_key_provider set not null;

alter table workflow_runs
  drop constraint if exists workflow_runs_model_preset_check,
  add constraint workflow_runs_model_preset_check check (model_preset in ('fast', 'quality')),
  drop constraint if exists workflow_runs_model_provider_check,
  add constraint workflow_runs_model_provider_check check (model_provider in ('openai', 'openrouter')),
  drop constraint if exists workflow_runs_api_key_provider_check,
  add constraint workflow_runs_api_key_provider_check check (api_key_provider in ('openai', 'openrouter'));

create table if not exists user_api_credentials (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  provider text not null,
  encrypted_api_key text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_api_credentials_provider_check check (provider in ('openai', 'openrouter')),
  constraint user_api_credentials_user_provider_unique unique (user_id, provider)
);

alter table user_api_credentials enable row level security;

drop policy if exists user_api_credentials_owner_policy on user_api_credentials;
create policy user_api_credentials_owner_policy on user_api_credentials
  for all using (auth.uid() = user_id);
