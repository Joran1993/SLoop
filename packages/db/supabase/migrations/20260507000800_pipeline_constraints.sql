set search_path = public, extensions;

-- Voorkom duplicaten per pand in pipeline_projects
-- Eerst dubbele rijen verwijderen (bewaar hoogste sloop_kans per pand)
delete from pipeline_projects a
using pipeline_projects b
where a.bag_pand_id = b.bag_pand_id
  and a.bag_pand_id is not null
  and a.sloop_kans < b.sloop_kans;

-- Dan pas de unique constraint toevoegen
alter table pipeline_projects
  add constraint uq_pipeline_project_pand unique (bag_pand_id);
