-- RW10+ production migration target: Supabase/PostgreSQL
create extension if not exists pgcrypto;
create type public.app_role as enum ('warga','ketua_rt','pengurus_rw','satpam_rw');
create type public.alert_mode as enum ('public','silent');
create type public.alert_status as enum ('cancel_window','active','acknowledged','responding','resolved','cancelled');

create table public.houses (
  id uuid primary key default gen_random_uuid(),
  rt smallint not null check (rt between 1 and 4),
  number text not null,
  address text not null,
  latitude numeric(10,7), longitude numeric(10,7),
  is_elderly_home boolean not null default false,
  created_at timestamptz not null default now(),
  unique (rt, number)
);

create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  house_id uuid references public.houses(id),
  full_name text not null,
  phone text not null unique,
  role public.app_role not null default 'warga',
  rt smallint not null check (rt between 1 and 4),
  theme text not null default 'system' check (theme in ('system','light','dark')),
  accessibility_mode boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.emergency_alerts (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references public.users(id),
  category text not null check (category in ('keamanan','medis','kebakaran','kecelakaan','bencana')),
  mode public.alert_mode not null,
  scope text not null check (scope in ('rt','rw','petugas')),
  status public.alert_status not null default 'cancel_window',
  latitude numeric(10,7), longitude numeric(10,7),
  address_snapshot text not null,
  cancel_deadline timestamptz not null,
  acknowledged_by uuid references public.users(id),
  acknowledged_at timestamptz,
  resolved_at timestamptz,
  resolution_code text,
  idempotency_key uuid not null,
  created_at timestamptz not null default now(),
  unique (reporter_id, idempotency_key)
);
create index emergency_active_idx on public.emergency_alerts(status, created_at desc) where status in ('cancel_window','active','acknowledged','responding');

create table public.dues_transactions (
  id uuid primary key default gen_random_uuid(), house_id uuid not null references public.houses(id),
  period date not null, amount_due bigint not null check(amount_due >= 0), amount_paid bigint not null default 0 check(amount_paid >= 0),
  status text not null check(status in ('belum_lunas','menunggu_verifikasi','lunas','ditolak')),
  payment_reference text, proof_url text, verified_by uuid references public.users(id), verified_at timestamptz,
  created_at timestamptz not null default now(), unique(house_id, period)
);
create index dues_period_idx on public.dues_transactions(period desc, status);

create table public.letters (
  id uuid primary key default gen_random_uuid(), requester_id uuid not null references public.users(id),
  letter_type text not null, purpose text not null,
  status text not null default 'submitted_rt' check(status in ('submitted_rt','rt_approved','revision','rejected','issued')),
  rt_note text, rw_note text, issued_number text unique, pdf_url text, verification_token_hash text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index letters_status_idx on public.letters(status, updated_at desc);

create table public.patrol_logs (
  id uuid primary key default gen_random_uuid(), guard_id uuid not null references public.users(id),
  checkpoint_id text not null, latitude numeric(10,7), longitude numeric(10,7),
  verification text not null check(verification in ('qr','nfc','manual_pilot')),
  valid boolean not null default false, created_at timestamptz not null default now()
);
create index patrol_latest_idx on public.patrol_logs(created_at desc);

create table public.guest_passes (
  id uuid primary key default gen_random_uuid(), owner_id uuid not null references public.users(id),
  guest_name text not null, purpose text not null, token_hash text not null unique,
  valid_from timestamptz not null default now(), valid_until timestamptz not null,
  status text not null default 'active' check(status in ('active','checked_in','checked_out','expired','revoked')),
  guard_id uuid references public.users(id), checked_in_at timestamptz, checked_out_at timestamptz,
  created_at timestamptz not null default now(), check(valid_until > valid_from)
);
create index guest_active_idx on public.guest_passes(status, valid_until) where status='active';

create table public.market_items (
  id uuid primary key default gen_random_uuid(), owner_id uuid not null references public.users(id),
  title text not null, category text not null, description text not null default '', price_label text not null,
  whatsapp text not null, image_url text, active boolean not null default true, created_at timestamptz not null default now()
);

create table public.voting_sessions (
  id uuid primary key default gen_random_uuid(), title text not null, description text not null default '',
  options jsonb not null check(jsonb_typeof(options)='array' and jsonb_array_length(options)>=2),
  status text not null default 'draft' check(status in ('draft','open','closed','published')),
  opens_at timestamptz not null, closes_at timestamptz not null, created_by uuid not null references public.users(id),
  created_at timestamptz not null default now(), check(closes_at > opens_at)
);
create table public.votes (
  id uuid primary key default gen_random_uuid(), session_id uuid not null references public.voting_sessions(id) on delete cascade,
  house_id uuid not null references public.houses(id), voter_id uuid not null references public.users(id), option_index integer not null,
  created_at timestamptz not null default now(), unique(session_id, house_id)
);

create or replace function public.my_profile() returns public.users language sql stable security definer set search_path=public as $$ select * from public.users where id=auth.uid() and active $$;
create or replace function public.is_role(roles public.app_role[]) returns boolean language sql stable security definer set search_path=public as $$ select exists(select 1 from public.users where id=auth.uid() and active and role=any(roles)) $$;
create or replace function public.my_rt() returns smallint language sql stable security definer set search_path=public as $$ select rt from public.users where id=auth.uid() $$;
create or replace function public.my_house() returns uuid language sql stable security definer set search_path=public as $$ select house_id from public.users where id=auth.uid() $$;

alter table public.houses enable row level security;
alter table public.users enable row level security;
alter table public.emergency_alerts enable row level security;
alter table public.dues_transactions enable row level security;
alter table public.letters enable row level security;
alter table public.patrol_logs enable row level security;
alter table public.guest_passes enable row level security;
alter table public.market_items enable row level security;
alter table public.voting_sessions enable row level security;
alter table public.votes enable row level security;

create policy users_self_read on public.users for select using(id=auth.uid() or public.is_role(array['pengurus_rw']::public.app_role[]));
create policy users_self_update on public.users for update using(id=auth.uid()) with check(id=auth.uid());
create policy houses_member_read on public.houses for select using(id=public.my_house() or public.is_role(array['ketua_rt','pengurus_rw','satpam_rw']::public.app_role[]));

create policy emergency_create on public.emergency_alerts for insert with check(reporter_id=auth.uid() and cancel_deadline<=now()+interval '11 seconds');
create policy emergency_reporter_read on public.emergency_alerts for select using(reporter_id=auth.uid());
create policy emergency_staff_read on public.emergency_alerts for select using(public.is_role(array['pengurus_rw','satpam_rw']::public.app_role[]) or (public.is_role(array['ketua_rt']::public.app_role[]) and exists(select 1 from public.users u where u.id=reporter_id and u.rt=public.my_rt()) and mode='public'));
create policy emergency_staff_update on public.emergency_alerts for update using(public.is_role(array['pengurus_rw','satpam_rw']::public.app_role[]) or (public.is_role(array['ketua_rt']::public.app_role[]) and exists(select 1 from public.users u where u.id=reporter_id and u.rt=public.my_rt()))) with check(true);

create policy dues_house_read on public.dues_transactions for select using(house_id=public.my_house() or public.is_role(array['pengurus_rw']::public.app_role[]) or (public.is_role(array['ketua_rt']::public.app_role[]) and exists(select 1 from public.houses h where h.id=house_id and h.rt=public.my_rt())));
create policy dues_rw_write on public.dues_transactions for all using(public.is_role(array['pengurus_rw']::public.app_role[])) with check(public.is_role(array['pengurus_rw']::public.app_role[]));
create policy letters_owner_create on public.letters for insert with check(requester_id=auth.uid());
create policy letters_scoped_read on public.letters for select using(requester_id=auth.uid() or public.is_role(array['pengurus_rw']::public.app_role[]) or (public.is_role(array['ketua_rt']::public.app_role[]) and exists(select 1 from public.users u where u.id=requester_id and u.rt=public.my_rt())));
create policy letters_approver_update on public.letters for update using(public.is_role(array['ketua_rt','pengurus_rw']::public.app_role[])) with check(public.is_role(array['ketua_rt','pengurus_rw']::public.app_role[]));

create policy patrol_read on public.patrol_logs for select using(true);
create policy patrol_guard_create on public.patrol_logs for insert with check(guard_id=auth.uid() and public.is_role(array['satpam_rw']::public.app_role[]));
create policy guest_owner_create on public.guest_passes for insert with check(owner_id=auth.uid());
create policy guest_scoped_read on public.guest_passes for select using(owner_id=auth.uid() or public.is_role(array['pengurus_rw','satpam_rw']::public.app_role[]));
create policy guest_guard_update on public.guest_passes for update using(public.is_role(array['pengurus_rw','satpam_rw']::public.app_role[])) with check(public.is_role(array['pengurus_rw','satpam_rw']::public.app_role[]));

create policy market_public_read on public.market_items for select using(active or owner_id=auth.uid() or public.is_role(array['pengurus_rw']::public.app_role[]));
create policy market_owner_write on public.market_items for insert with check(owner_id=auth.uid());
create policy market_owner_update on public.market_items for update using(owner_id=auth.uid() or public.is_role(array['pengurus_rw']::public.app_role[]));
create policy voting_read on public.voting_sessions for select using(status in ('open','closed','published') or public.is_role(array['pengurus_rw']::public.app_role[]));
create policy voting_rw_write on public.voting_sessions for all using(public.is_role(array['pengurus_rw']::public.app_role[])) with check(public.is_role(array['pengurus_rw']::public.app_role[]));
create policy vote_once_create on public.votes for insert with check(voter_id=auth.uid() and house_id=public.my_house());
create policy votes_owner_read on public.votes for select using(voter_id=auth.uid() or public.is_role(array['pengurus_rw']::public.app_role[]));

alter publication supabase_realtime add table public.emergency_alerts, public.patrol_logs, public.letters;
