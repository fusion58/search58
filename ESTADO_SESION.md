# Estado de la sesión

> Bitácora viva. Lo más reciente arriba.

## 2026-08-12 — Mejoras de geocodificación y búsqueda

### Geocodificación inversa (/reverse)
- **Threshold subido 13 → 15:** F58 necesita road+sector para ganar sin comparar
- **Scoring mejorado:** postcode +2 pts, city con "parroquia" = 0 pts
- **Zonas marítimas (tiletype=0):** F58 retorna directo sin llamar Nominatim (Mar Caribe, zonas costeras)
- **Mapa F58 en comparador:** proxy `/geoserver/` en FastAPI → GeoServer QA :8080, tiles MVT F58-Map
- **Frontend comparador:** ganador basado en `source` de la API (no re-score JS), relieve/edificios apagados por defecto

### Búsqueda por texto (/search)
- **Mínimo 3 caracteres:** 1-2 letras causaban queries de 6+ segundos (word_similarity masivo)
- **Geo re-ranking:** palabras del query vs ubicación completa con stem matching — "residencias las vegas caracas" retorna Caracas primero
- **GeoNames Venezuela:** 56,081 registros (ríos, cerros, lagos, parques) en `buscador.geonames`; si query contiene indicador geográfico (río, cerro, lago, parque...) → GeoNames primero
- **Normalización Nominatim:** display_name con puntos en lugar de comas (igual que F58)
- **Fallback Nominatim:** solo cuando F58 y GeoNames no tienen resultados

### Infraestructura y rendimiento
- **4 workers uvicorn** (antes 2), pool psycopg2 20 conexiones
- **Índices GIST nuevos:** `country_tiles_geom_idx`, `roadsegments_862_country_geom_idx`, `order9area_862_country_geom_idx`
- **Tuning PostgreSQL:** shared_buffers 512MB, work_mem 16MB, random_page_cost 1.1 (SSD)
- **Benchmark:** 33.9 req/s, p95 636ms (antes 27.6 req/s / p95 965ms)
- **Frontend simulación:** click en fila centra mapa, pts/s en vivo, tiempo máximo en rojo
- **GeoNames en QA:** tabla cargada con script `infra/load_geonames.py`

### Issues
- #6 CLOSED — GeoNames Venezuela (PR #7 mergeado)
- #4 OPEN — apuntar Traccar/Route58 a `http://100.75.222.2:7171`

### Próximos pasos
- Issue #4: cambiar `geocoder.url` en Traccar/Route58
- Redis caché: mayor impacto en throughput para coordenadas repetidas de Traccar
- Fallback a Nominatim si BD de F58 cae (resiliencia)
- Nominatim self-hosted Venezuela (sin rate limit)

## 2026-08-07 — Arranque QA completado

- **Stack en QA:** postgres (postgis:17-3.5) + search58-api:1.0 en Docker, servidor `100.75.222.2:7171` vía Tailscale.
- **BD migrada:** esquema `buscador` desde `localhost:5433` — funciones `f_geocodificacion_inversa`, `f_search_in_country` + datos Venezuela. Extensión `pg_trgm` instalada manualmente (necesaria para búsqueda por texto).
- **Validado:** `/health` → `{"status":"ok"}`, `/reverse?lat=10.4806&lon=-66.9036` → Caracas score 23 (F58), `/search?q=Altamira` → 3 resultados F58.
- **Latencia:** ~500 ms por request (vs 2200 ms dev server con subprocess psql). Margen de mejora con índices GIN restaurados.
- **Issues cerrados:** #2 (FastAPI), #3 (compose). PR #5 abierto en GitHub.
- **Issues abiertos:** #1 (BD a QA — se cierra con el merge del PR), #4 (integración Traccar — pendiente).
- **Pendiente:** merge PR #5 → cerrar #1 → issue #4 (apuntar Traccar a `http://100.75.222.2:7171`).

## 2026-08-06 — Diseño completo + herramientas de validación implementadas

- **Arquitectura decidida:** proxy híbrido F58 + Nominatim. Score ≥ 13 → F58 directo; score < 13 → Nominatim como fallback.
- **Dev server operativo** en `localhost:7171`: endpoints `/reverse` (híbrido), `/search`, proxy `/geoserver/`.
- **Frontend:**
  - `geocode-compare.html` — comparador lado a lado con badge verde al ganador y barras de score.
  - `simulation.html` — simulación en tiempo real: N puntos aleatorios en Venezuela, mapa con puntos coloreados por fuente, tabla con dirección/fuente/ms, descarga CSV.
- **Benchmark:** 1000 puntos aleatorios → 59.6% con dirección completa, 4.2 req/s (limitado por subprocess psql del dev server; FastAPI estimado: 50-200 req/s).
- **BD buscador (localhost:5433):** `country_tiles` Venezuela (2374 tiles) copiados desde 5452. Bugs corregidos: `f_identify`, `f_identify_speed_limit`, `f_search_by_code` (SQL injection), `f_search_in_xy` (distancia DESC→ASC), `construir_direccion` WHEN 6.
- **Spec:** `docs/superpowers/specs/2026-08-06-search58-design.md`
- **Pendiente:** crear repo GitHub `fusion58/search58` → issues #1-#4 (BD a QA, FastAPI, compose, integración Traccar).

## 2026-08-05 — Arranque del repo local

- Estructura estándar Fusión58 creada en `D:\Docker\search58`.
- **Pendiente:** crear repo en GitHub (`fusion58/search58`), abrir issue #1 (arranque QA), definir stack (Nominatim vs alternativa), confirmar llave SSH del server QA.
- **Próximo paso:** brainstorming de stack → issue #1 → repo GitHub → deploy QA.
