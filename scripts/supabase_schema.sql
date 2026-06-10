-- Agent runs observability table for ai-orch
-- Run this in your Supabase project SQL editor before using: ai-orch observe

create table if not exists agent_runs (
  id          bigserial primary key,
  agent_id    text        not null,
  command     text        not null,
  timestamp   timestamptz not null default now(),
  tokens_in   integer     not null default 0,
  tokens_out  integer     not null default 0,
  latency_ms  integer     not null default 0,
  cost_usd    numeric(10,6) not null default 0,
  status      text        not null default 'ok',
  eval_score  numeric(4,3)
);

create index if not exists idx_agent_runs_agent_id  on agent_runs(agent_id);
create index if not exists idx_agent_runs_timestamp on agent_runs(timestamp desc);
create index if not exists idx_agent_runs_status    on agent_runs(status);
