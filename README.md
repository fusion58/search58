# Search58

Proxy inteligente de geocodificación para Fusión58. Recibe coordenadas GPS en formato Nominatim y devuelve la dirección legible correspondiente, combinando múltiples fuentes de datos con prioridad en la base de datos geoespacial propia (F58).

## Propósito

Route58 necesita bautizar puntos de posición GPS con su dirección real. Search58 actúa como el geocodificador centralizado de toda la plataforma Fusión58: un único endpoint compatible con el formato Nominatim al que apuntan Route58 y cualquier otro cliente.

## Fuentes de datos

| Prioridad | Fuente | Cobertura |
|---|---|---|
| 1 | **F58** — BD PostgreSQL/PostGIS propia | Venezuela, detalle callejero |
| 2 | **GeoNames** — BD local 56K registros | Geografía natural VE (ríos, cerros, parques) |
| 3 | **Photon** (photon.komoot.io) | Mundial, sin rate limit, base OSM |
| 4 | **Nominatim** (OSM público) | Mundial, fallback final |

## Endpoints

### `GET /reverse`
Geocodificación inversa — convierte coordenadas GPS en dirección.

```
GET /reverse?lat=10.4806&lon=-66.9036
```

```json
{
  "display_name": "Avenida Nueva Granada entre Avenida Luisa Cáceres de Arismendi y Avenida Roosevelt. La Bandera. Caracas. Parroquia Santa Rosalía. Municipio Libertador. Distrito Capital. Venezuela.",
  "lat": "10.4806",
  "lon": "-66.9036",
  "source": "f58",
  "score": 23,
  "address": {
    "road": "Avenida Nueva Granada",
    "neighbourhood": "La Bandera",
    "city": "Caracas",
    "county": "Municipio Libertador",
    "state": "Estado Distrito Capital",
    "country": "Venezuela",
    "country_code": "ve"
  }
}
```

El campo `source` indica qué fuente resolvió la petición: `f58`, `photon` o `nominatim`.

### `GET /search`
Búsqueda de lugares por texto.

```
GET /search?q=Altamira&limit=10
GET /search?q=Torre+Exa&limit=10&sources=all
```

Con `sources=all` consulta F58 + Photon + Nominatim en paralelo, mezcla y deduplica por proximidad geográfica.

### `GET /health`
Estado del servicio.

```json
{ "status": "ok", "db": "connected" }
```

### `GET /sample-points`
N coordenadas aleatorias de Venezuela (para pruebas y simulaciones).

```
GET /sample-points?n=100
```

## Lógica híbrida `/reverse`

```
1. Consultar F58 local (siempre)
2. Si score F58 ≥ 15 → retornar F58 directo
3. Si tiletype = 0 (mar/costa/zona insular) → retornar F58 directo
4. Si score < 15 → consultar Photon y Nominatim
5. Retornar el de mayor score; empate → F58
```

**Scoring (máx 25 pts):**

| Campo | Pts |
|---|---|
| road (calle/vía) | 10 |
| neighbourhood (sector/urb.) | 5 |
| city (ciudad) | 3 |
| county (municipio) | 2 |
| state (estado) | 2 |
| country (país) | 1 |
| postcode (código postal) | 2 |

## Stack técnico

- **API:** Python 3.12 + FastAPI + uvicorn (4 workers)
- **BD:** PostgreSQL 17 + PostGIS 3.5 (imagen `postgis/postgis:17-3.5`)
- **Datos:** esquema `buscador` — funciones F58, GeoNames Venezuela
- **Contenedores:** `postgres` + `search58-api` en red Docker `search58`
- **Datos en disco:** bind mount `/opt/search58/postgres` (fuera del contenedor)

## Rendimiento (QA — servidor 4 CPUs, 8GB RAM, SSD)

| Métrica | Valor |
|---|---|
| Throughput | ~34 req/s |
| Latencia p50 | ~475 ms |
| Latencia p95 | ~636 ms |
| F58 cobertura VE | ~95% de los puntos |

## Herramientas de validación

Disponibles en `http://<servidor>:7171/`:

- **`/geocode-compare.html`** — Comparador lado a lado: Nominatim · Photon · Search58. Clic en el mapa o ingresa coordenadas `lon, lat`.
- **`/simulation.html`** — Simulación de N puntos GPS aleatorios en Venezuela con estadísticas en tiempo real.

## Deploy QA

Ver [`docs/INTEGRACION-ROUTE58.md`](docs/INTEGRACION-ROUTE58.md) para configuración completa.

```bash
# En el servidor QA
docker compose --env-file .env -f infra/docker-compose.yml up -d
```

## Variables de entorno

Ver [`.env.example`](.env.example).

| Variable | Default | Descripción |
|---|---|---|
| `POSTGRES_PASSWORD` | — | **Requerida** |
| `POSTGRES_DB` | `buscador` | Nombre de la BD |
| `HYBRID_THRESHOLD` | `15` | Score mínimo F58 para no llamar a fuentes externas |
| `NOMINATIM_TIMEOUT` | `5` | Timeout (segundos) para llamadas a Photon/Nominatim |
| `PHOTON_URL` | `https://photon.komoot.io` | URL del servicio Photon |
| `GEOSERVER_URL` | `http://localhost:8080` | GeoServer para proxy de tiles MVT |
| `SEARCH58_PORT` | `7171` | Puerto expuesto |

## Issues abiertos

- [#4](https://github.com/fusion58/search58/issues/4) — Integrar Search58 con Route58 (cambiar `geocoder.url`)
