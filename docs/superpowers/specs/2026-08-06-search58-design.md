# Search58 — Diseño del Servicio

**Fecha:** 2026-08-06  
**Estado:** Aprobado (implementación parcial validada localmente)

---

## 1. Propósito

Search58 es un proxy inteligente de geocodificación para Fusión58. Recibe peticiones de cualquier cliente (Traccar, Route58, mapas) en formato Nominatim y decide internamente qué fuente usar: la base de datos geoespacial propia (F58) o el servicio público de Nominatim (OSM).

**Problema que resuelve:**
- Traccar/Route58 llama a Nominatim externo → límite 1 req/s, privacidad, dependencia de internet
- Los datos propios de Venezuela son más completos y detallados que OSM en muchas zonas
- Se necesita un único punto de configuración para todos los clientes actuales y futuros

---

## 2. Arquitectura

```
Traccar / Route58 / otros clientes
        │
        ▼
  Search58 API  (puerto 7171 en dev; puerto a definir en QA)
  ┌────────────────────────────────────────────┐
  │  GET /reverse?lat=X&lon=Y                  │
  │  GET /search?q=TEXT&limit=N                │
  │                                            │
  │  ┌──────────────┐    ┌──────────────────┐ │
  │  │  F58 local   │    │  Nominatim       │ │
  │  │  PostgreSQL  │    │  (internet,      │ │
  │  │  (< 50ms)    │    │   fallback)      │ │
  │  └──────┬───────┘    └────────┬─────────┘ │
  │         └────────┬────────────┘           │
  │                  ▼                        │
  │           score_address()                 │
  │           → elige la más completa         │
  └──────────────────────────────────────────-┘
```

**Dos contenedores Docker en QA:**
- `postgres` — PostgreSQL/PostGIS con la BD `buscador`; datos en `/opt/search58/postgres`
- `search58-api` — Python/FastAPI; expone `:7171` hacia Tailscale

---

## 3. Lógica híbrida

### Scoring de completitud (máx 23 pts)

| Campo | Puntos |
|---|---|
| road (calle/carretera) | 10 |
| neighbourhood (urbanización/sector) | 5 |
| city (ciudad) | 3 |
| county (municipio) | 2 |
| state (estado) | 2 |
| country (país) | 1 |

### Algoritmo de decisión

1. **Consultar F58** (local, siempre): `f_geocodificacion_inversa(point)`
2. **Si score F58 ≥ 13** (tiene calle + ciudad) → retornar F58 **de inmediato**, sin llamar a Nominatim
3. **Si score F58 < 13** → consultar Nominatim (timeout 5s)
4. **Comparar scores** → retornar el de mayor score; empate → F58 (local, privado)
5. **Si Nominatim falla** → retornar F58 aunque sea parcial
6. **Si ambos fallan** → `"Sin información"` con HTTP 200 (Traccar no debe romper)

**Umbral elegido (13):** cubre los casos donde F58 tiene al menos calle + ciudad, que es la dirección útil para bautizar un punto GPS.

### Campo `source` en la respuesta

Cada respuesta incluye `"source": "f58"` o `"source": "nominatim"` — Traccar lo ignora pero es útil para monitoreo y la herramienta de comparación.

---

## 4. Endpoints (formato Nominatim exacto)

### `GET /reverse`

```
GET /reverse?format=json&lat=10.4806&lon=-66.9036
```

Respuesta:
```json
{
  "display_name": "Av. Nueva Granada entre...",
  "lat": "10.4806",
  "lon": "-66.9036",
  "source": "f58",
  "score": 18,
  "address": {
    "road":          "Avenida Nueva Granada",
    "neighbourhood": "La Bandera",
    "city":          "Caracas",
    "county":        "Municipio Libertador",
    "state":         "Distrito Capital",
    "country":       "Venezuela",
    "country_code":  "ve"
  }
}
```

### `GET /search`

```
GET /search?format=json&q=Altamira&limit=10&countrycodes=ve
```

Respuesta (array Nominatim):
```json
[
  {
    "display_name": "Altamira, Caracas...",
    "lat": "10.4943", "lon": "-66.8490",
    "boundingbox": ["10.48","10.51","-66.86","-66.84"],
    "type": "Centro Poblado",
    "source": "f58"
  }
]
```

### `GET /health`

```json
{ "status": "ok", "db": "connected" }
```

---

## 5. Mapping F58 → OSM

| Campo OSM/Nominatim | Campo F58 (`t_geographical_position`) |
|---|---|
| `road` | `nameurbanroads` o `nametownroads` |
| `neighbourhood` | `nameorder9area` (urbanización/sector) |
| `city` | `nameorder8area` |
| `county` | `denominationorder2area + nameorder2area` |
| `state` | `denominationorder1area + nameorder1area` |
| `country` | `namecountry` |
| `country_code` | derivado de `namecountry` (Venezuela → "ve") |

---

## 6. Stack de producción

| Componente | Tecnología | Justificación |
|---|---|---|
| Servicio HTTP | Python + FastAPI | mínimo código, async nativo, OpenAPI auto, extensible |
| BD → Python | psycopg2 + connection pool | sin subprocess, sin startup de proceso por request |
| Contenedor | Docker (imagen Python slim) | consistente con el resto del stack Fusión58 |
| Proxy → clientes | Exposición directa por Tailscale | misma arquitectura que ServiceMap |

**Rendimiento esperado en FastAPI (vs dev server):**

| Métrica | Dev server (subprocess) | FastAPI (psycopg2) |
|---|---|---|
| Latencia F58 | ~2 200 ms | 30–100 ms |
| Latencia híbrida | ~2 200 ms + 5s Nominatim | 30–100 ms + timeout Nominatim |
| Throughput | 4 req/s | 50–200 req/s |

La diferencia viene de eliminar el spawn de proceso `psql` por petición.

---

## 7. Estructura del repo

```
search58/
├── api/
│   ├── main.py           # FastAPI app: /reverse, /search, /health
│   ├── db.py             # pool de conexiones psycopg2
│   ├── geocoder.py       # geocode_hybrid, geocode_nominatim, score_address
│   └── requirements.txt  # fastapi, uvicorn, psycopg2-binary
├── Dockerfile
├── frontend/
│   ├── geocode-compare.html  # comparador lado a lado
│   ├── simulation.html       # simulación en tiempo real
│   └── server-dev.py         # dev server local (reemplazado por FastAPI en QA)
└── infra/
    └── docker-compose.yml    # postgres + search58-api
```

---

## 8. Deploy QA

```
/opt/search58/
├── .env                  # secretos (chmod 600)
├── infra/
│   └── docker-compose.yml
└── postgres/             # datos BD buscador (bind mount)
```

**Datos a migrar a QA:**
- BD `buscador` completa desde `localhost:5433` → pg_dump + restore en QA
- Incluye: esquema buscador, `country_tiles` Venezuela (2374 tiles), `roadsegments_862` (304K), `buscador_862` (465K)

**Integración con Route58/Traccar (único cambio):**
```xml
<!-- traccar.xml -->
<entry key='geocoder.type'>nominatim</entry>
<entry key='geocoder.url'>http://100.75.222.2:7171</entry>
```

---

## 9. Herramientas de validación (ya construidas)

- **`frontend/geocode-compare.html`** — comparación lado a lado de un punto (clic en mapa → address de Nominatim vs F58, badge verde al ganador)
- **`frontend/simulation.html`** — simulación de N puntos aleatorios: mapa en tiempo real con puntos coloreados por fuente, tabla con dirección/fuente/ms, descarga CSV
- **`benchmark_search58.csv`** — resultado de prueba con 1000 puntos (59.6% con dirección, 4.2 req/s en dev server)

---

## 10. Pendiente de implementación

- [ ] Issue #1: migrar BD `buscador` a QA (`/opt/search58/postgres`)
- [ ] Issue #2: `api/` FastAPI con psycopg2 pool + Dockerfile
- [ ] Issue #3: `infra/docker-compose.yml` (postgres + search58-api)
- [ ] Issue #4: integrar con Route58/Traccar (cambiar `geocoder.url`)
- [ ] Crear repo `fusion58/search58` en GitHub

---

## 11. Decisiones de diseño y justificación

| Decisión | Alternativa rechazada | Razón |
|---|---|---|
| Proxy híbrido en Search58 | Configurar Traccar directamente contra Nominatim | Search58 como punto único; futura mejora de datos sin tocar clientes |
| F58 primero, Nominatim como fallback | Paralelo con race | Evita llamadas innecesarias al API público; privacidad de coordenadas GPS |
| Umbral score 13 | Score más bajo o más alto | 13 = calle + ciudad: suficiente para bautizar un punto GPS |
| Python + FastAPI | Node.js, PostgREST | Mismo lenguaje que herramientas de dev; mínimo código para API Nominatim-compatible |
| Puerto 7171 (dev) | 7070 | AnyDesk ocupa 7070 permanentemente en este equipo |
