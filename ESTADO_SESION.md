# Estado de la sesión

> Bitácora viva. Lo más reciente arriba.

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
