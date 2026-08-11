-- Search58 — PostgreSQL tuning para servidor QA/prod (SSD, 8GB RAM)
-- Aplicar con: psql -U postgres -f postgres-tuning.sql
-- Requiere reinicio del servicio postgres para shared_buffers

-- Memoria
ALTER SYSTEM SET shared_buffers       = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem             = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';

-- Planner: costos para SSD (default es HDD, random_page_cost=4)
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET seq_page_cost    = '1.0';

SELECT pg_reload_conf();

-- Indices espaciales (ejecutar en buscador DB)
-- country_tiles: no tenia GIST — era Seq Scan en cada peticion
CREATE INDEX IF NOT EXISTS country_tiles_geom_idx
  ON buscador.country_tiles USING GIST (the_geom);

-- Indices parciales codecountry=862 (Venezuela) — mas selectivos que el GIST global
CREATE INDEX CONCURRENTLY IF NOT EXISTS roadsegments_862_country_geom_idx
  ON buscador.roadsegments_862 USING GIST (the_geom) WHERE codecountry = 862;

CREATE INDEX CONCURRENTLY IF NOT EXISTS order9area_862_country_geom_idx
  ON buscador.order9area_862 USING GIST (the_geom) WHERE codecountry = 862;

-- Actualizar estadisticas despues de crear indices
VACUUM ANALYZE buscador.country_tiles;
VACUUM ANALYZE buscador.roadsegments_862;
VACUUM ANALYZE buscador.order9area_862;
VACUUM ANALYZE buscador.order8area_862;
VACUUM ANALYZE buscador.order3area_862;
