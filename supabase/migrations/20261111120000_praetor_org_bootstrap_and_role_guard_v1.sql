-- PRAETOR Intelligence: harden multi-tenant authorization and organization bootstrap.
-- Applied to the connected Supabase project as migration
-- praetor_org_bootstrap_and_role_guard_v1.

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

alter function public.is_org_member(uuid) set schema private;
alter function public.has_org_role(uuid, text[]) set schema private;

revoke all on function private.is_org_member(uuid) from public, anon;
revoke all on function private.has_org_role(uuid, text[]) from public, anon;
grant execute on function private.is_org_member(uuid) to authenticated;
grant execute on function private.has_org_role(uuid, text[]) to authenticated;

revoke all on function public.handle_new_user() from public, anon, authenticated;

drop policy if exists "organizations_select_members" on public.organizations;
create policy "organizations_select_members" on public.organizations
for select to authenticated using (private.is_org_member(id));

drop policy if exists "organizations_update_admins" on public.organizations;
create policy "organizations_update_admins" on public.organizations
for update to authenticated
using (private.has_org_role(id, array['owner','admin']))
with check (private.has_org_role(id, array['owner','admin']));

drop policy if exists "members_select_org" on public.organization_members;
create policy "members_select_org" on public.organization_members
for select to authenticated using (private.is_org_member(organization_id));
drop policy if exists "members_insert_admins" on public.organization_members;
create policy "members_insert_admins" on public.organization_members
for insert to authenticated
with check (private.has_org_role(organization_id, array['owner','admin']));
drop policy if exists "members_update_admins" on public.organization_members;
create policy "members_update_admins" on public.organization_members
for update to authenticated
using (private.has_org_role(organization_id, array['owner','admin']))
with check (private.has_org_role(organization_id, array['owner','admin']));
drop policy if exists "members_delete_admins" on public.organization_members;
create policy "members_delete_admins" on public.organization_members
for delete to authenticated
using (private.has_org_role(organization_id, array['owner','admin']));

drop policy if exists "leads_select_org" on public.leads;
create policy "leads_select_org" on public.leads
for select to authenticated using (private.is_org_member(organization_id));
drop policy if exists "leads_insert_org" on public.leads;
create policy "leads_insert_org" on public.leads
for insert to authenticated
with check (private.has_org_role(organization_id, array['owner','admin','analyst']));
drop policy if exists "leads_update_org" on public.leads;
create policy "leads_update_org" on public.leads
for update to authenticated
using (private.has_org_role(organization_id, array['owner','admin','analyst']))
with check (private.has_org_role(organization_id, array['owner','admin','analyst']));
drop policy if exists "leads_delete_admins" on public.leads;
create policy "leads_delete_admins" on public.leads
for delete to authenticated
using (private.has_org_role(organization_id, array['owner','admin']));

drop policy if exists "reports_select_org" on public.reports;
create policy "reports_select_org" on public.reports
for select to authenticated using (private.is_org_member(organization_id));
drop policy if exists "reports_insert_org" on public.reports;
create policy "reports_insert_org" on public.reports
for insert to authenticated
with check (private.has_org_role(organization_id, array['owner','admin','analyst']));
drop policy if exists "reports_update_org" on public.reports;
create policy "reports_update_org" on public.reports
for update to authenticated
using (private.has_org_role(organization_id, array['owner','admin','analyst']))
with check (private.has_org_role(organization_id, array['owner','admin','analyst']));
drop policy if exists "reports_delete_admins" on public.reports;
create policy "reports_delete_admins" on public.reports
for delete to authenticated
using (private.has_org_role(organization_id, array['owner','admin']));

create or replace function public.create_organization_with_owner(p_name text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
  v_org_id uuid;
  v_name text := btrim(p_name);
begin
  if v_user_id is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if v_name is null or length(v_name) < 2 or length(v_name) > 120 then
    raise exception 'Organization name must contain between 2 and 120 characters' using errcode = '22023';
  end if;

  insert into public.organizations (name, created_by)
  values (v_name, v_user_id)
  returning id into v_org_id;

  insert into public.organization_members (organization_id, user_id, role)
  values (v_org_id, v_user_id, 'owner');

  return v_org_id;
end;
$$;

revoke all on function public.create_organization_with_owner(text) from public, anon;
grant execute on function public.create_organization_with_owner(text) to authenticated;

-- Direct role edits are disabled for client roles in V1. Role changes must
-- go through a separately audited administrative operation.
revoke update (role) on public.organization_members from anon, authenticated;

create index if not exists idx_organizations_created_by
  on public.organizations(created_by);
create index if not exists idx_reports_lead_id
  on public.reports(lead_id);
