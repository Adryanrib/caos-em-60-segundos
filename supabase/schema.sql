-- Estrutura para futura integração. Não expor service_role ao navegador.
create table if not exists public.sources (
 id uuid primary key default gen_random_uuid(),
 platform text not null check (platform in ('twitch','youtube')),
 channel text not null,
 enabled boolean not null default true,
 rights_verified boolean not null default false,
 created_at timestamptz not null default now(),
 unique(platform, channel)
);
create table if not exists public.clips (
 id uuid primary key default gen_random_uuid(),
 source_id uuid references public.sources(id) on delete set null,
 platform_clip_id text not null unique,
 title text,
 original_url text,
 views bigint not null default 0,
 status text not null default 'discovered' check (status in ('discovered','queued','rendered','published','failed')),
 created_at timestamptz not null default now()
);
alter table public.sources enable row level security;
alter table public.clips enable row level security;
-- Sem políticas públicas: somente backend autorizado via service role pode acessar.
