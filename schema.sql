-- Run ONCE in Supabase SQL Editor. All writes are transactional and service-only.
create table if not exists public.paper_state (
 id integer primary key check (id=1),
 version bigint not null default 0,
 cash numeric not null check (cash >= 0),
 holdings jsonb not null default '{}'::jsonb,
 pending jsonb,
 updated_at timestamptz not null default now()
);
insert into public.paper_state(id,version,cash,holdings,pending)
values (1,0,5000,'{}',null) on conflict(id) do nothing;
create table if not exists public.paper_runs (
 market_date date primary key,
 equity numeric not null,
 cash numeric not null,
 spy_price numeric not null,
 ranking jsonb not null,
 rationale text not null,
 created_at timestamptz not null default now()
);
create table if not exists public.paper_trades (
 id bigint generated always as identity primary key,
 market_date date not null references public.paper_runs(market_date),
 ticker text not null,
 side text not null check (side in ('BUY','SELL')),
 quantity numeric not null check (quantity > 0),
 price numeric not null check (price > 0),
 notional numeric not null check (notional >= 0),
 fee numeric not null check (fee >= 0)
);
alter table public.paper_state enable row level security;
alter table public.paper_runs enable row level security;
alter table public.paper_trades enable row level security;
revoke all on public.paper_state,public.paper_runs,public.paper_trades from anon,authenticated;
-- Invoked using service_role only; never expose service_role to browser clients.
create or replace function public.commit_paper_day(
 p_expected_version bigint, p_market_date date, p_cash numeric,
 p_holdings jsonb,p_pending jsonb,p_equity numeric,p_spy_price numeric,
 p_ranking jsonb,p_trades jsonb,p_rationale text
) returns jsonb language plpgsql security invoker set search_path=public as $$
declare v_version bigint; v_trade jsonb;
begin
 select version into v_version from paper_state where id=1 for update;
 if v_version is distinct from p_expected_version then
  raise exception 'Concurrent update: expected %, actual %',p_expected_version,v_version;
 end if;
 if exists(select 1 from paper_runs where market_date=p_market_date) then
  return jsonb_build_object('status','already_processed','date',p_market_date);
 end if;
 if p_cash < 0 or p_equity <= 0 or p_spy_price <= 0 then
  raise exception 'Invalid paper state or price';
 end if;
 insert into paper_runs(market_date,equity,cash,spy_price,ranking,rationale)
 values(p_market_date,p_equity,p_cash,p_spy_price,p_ranking,p_rationale);
 for v_trade in select * from jsonb_array_elements(p_trades) loop
  insert into paper_trades(market_date,ticker,side,quantity,price,notional,fee)
  values(p_market_date,v_trade->>'ticker',v_trade->>'side',
   (v_trade->>'quantity')::numeric,(v_trade->>'price')::numeric,
   (v_trade->>'notional')::numeric,(v_trade->>'fee')::numeric);
 end loop;
 update paper_state set version=version+1,cash=p_cash,holdings=p_holdings,
 pending=p_pending,updated_at=now() where id=1;
 return jsonb_build_object('status','committed','date',p_market_date,'trades',jsonb_array_length(p_trades));
end;$$;
revoke execute on function public.commit_paper_day(bigint,date,numeric,jsonb,jsonb,numeric,numeric,jsonb,jsonb,text) from public,anon,authenticated;
grant execute on function public.commit_paper_day(bigint,date,numeric,jsonb,jsonb,numeric,numeric,jsonb,jsonb,text) to service_role;
