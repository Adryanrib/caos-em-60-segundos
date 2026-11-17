-- Rodar no SQL Editor do projeto pessoal; não elimina registros anteriores.
alter table public.clip_queue
  add column if not exists media_path text,
  add column if not exists rendered_at timestamptz;

-- Permissões ficam no backend; os clipes não são públicos.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('caos60-shorts', 'caos60-shorts', false, 52428800, array['video/mp4'])
on conflict (id) do nothing;

create index if not exists clip_queue_rendered_at_idx
on public.clip_queue (rendered_at desc)
where rendered_at is not null;
