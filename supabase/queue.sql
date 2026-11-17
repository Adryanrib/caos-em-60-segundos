-- Execute no SQL Editor do Supabase pessoal.
create table if not exists public.clip_queue (
  id uuid primary key default gen_random_uuid(),
  clip_id uuid not null unique references public.clips(id) on delete cascade,
  status text not null default 'awaiting_media'
    check (status in ('awaiting_media','media_ready','rendering','rendered','publishing','published','failed')),
  rank_score numeric(8,2) not null default 0,
  selected_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  error_message text
);
create index if not exists clip_queue_selected_at_idx on public.clip_queue(selected_at desc);
alter table public.clip_queue enable row level security;
revoke all on public.clip_queue from anon, authenticated;
