# Search58 — Plan de Arranque QA

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levantar Search58 en el servidor QA (`100.75.222.2`) con FastAPI + PostgreSQL/PostGIS en Docker, exponiendo `/reverse` y `/search` en el puerto 7171 via Tailscale.

**Architecture:** Dos contenedores Docker (`postgres` y `search58-api`) en la red `search58`. La BD `buscador` se migra desde `localhost:5433` via pg_dump → scp → pg_restore. La API FastAPI usa psycopg2 con connection pool en lugar del subprocess psql del dev server.

**Tech Stack:** Python 3.12, FastAPI 0.115, uvicorn, psycopg2-binary, postgis/postgis:17-3.5, Docker Compose.

## Global Constraints

- Idioma de commits y PR: español convencional (`feat(scope): ...`)
- Identidad git: `git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco'`
- Issue-first: cada tarea cierra su issue con `Closes #N`
- Puerto API en QA: 7171 (mismo que dev; AnyDesk ocupa 7070)
- PostgreSQL image QA: `postgis/postgis:17-3.5` (PG 17 LTS + PostGIS 3.5)
- pg_dump a usar: `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe` (versión 18, coincide con el servidor local)
- SSH key QA: `~/.ssh/vps_qa` → `root@100.75.222.2`
- Datos QA en `/opt/search58/` (bind mount fuera del contenedor)
- Deploy: `docker compose --env-file .env -f infra/docker-compose.yml up -d`
- Imagen nunca `latest` — siempre versión fija

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `api/requirements.txt` | Crear | Dependencias Python del servicio |
| `api/db.py` | Crear | Pool de conexiones psycopg2 |
| `api/geocoder.py` | Crear | Lógica híbrida F58 + Nominatim |
| `api/main.py` | Crear | FastAPI app: /reverse, /search, /health |
| `Dockerfile` | Crear | Imagen search58-api |
| `infra/docker-compose.yml` | Modificar | Stack completo postgres + search58-api |
| `.env.example` | Crear | Plantilla de variables de entorno |
| `ESTADO_SESION.md` | Modificar | Actualizar estado al finalizar cada tarea |
| `docs/MODIFICACIONES.md` | Modificar | Registrar el stack QA |
| `VINCULACIONES.md` | Modificar | Añadir vínculo api/ ↔ Dockerfile ↔ compose |

---

## Task 1: GitHub repo, push inicial e issues

**Files:**
- (ningún archivo; solo acciones de git/gh)

**Interfaces:**
- Produce: repo `fusion58/search58` público con 4 issues abiertos; base de trabajo para las tareas siguientes

- [ ] **Step 1: Crear el repo en GitHub**

```bash
gh repo create fusion58/search58 \
  --public \
  --description "Proxy de geocodificación inversa F58+Nominatim para Route58/Traccar" \
  --source . \
  --remote origin \
  --push
```

Esperado: URL `https://github.com/fusion58/search58` creada y código en `main`.

- [ ] **Step 2: Verificar que el push llegó**

```bash
gh repo view fusion58/search58 --json name,url,defaultBranchRef
```

Esperado: `"name": "search58"`, `"defaultBranchRef": {"name": "main"}`.

- [ ] **Step 3: Crear issue #1 — Migrar BD buscador a QA**

```bash
gh issue create \
  --repo fusion58/search58 \
  --title "feat(infra): migrar BD buscador al servidor QA" \
  --body "Migrar la BD \`buscador\` desde \`localhost:5433\` al servidor QA (\`100.75.222.2\`) via pg_dump → scp → pg_restore en contenedor postgis/postgis:17-3.5.

**Datos a migrar (solo esquema buscador):**
- Funciones: f_geocodificacion_inversa, f_search_in_country, etc.
- Tablas: buscador_862, roadsegments_862, referencepoints_862, country_tiles (Venezuela)
- Extensiones: PostGIS, fuzzystrmatch

**Criterio de aceptación:** \`curl http://100.75.222.2:7171/health\` devuelve \`{\"status\":\"ok\",\"db\":\"connected\"}\`"
```

- [ ] **Step 4: Crear issue #2 — FastAPI + Dockerfile**

```bash
gh issue create \
  --repo fusion58/search58 \
  --title "feat(api): FastAPI con psycopg2 pool + Dockerfile" \
  --body "Reemplazar el dev server (subprocess psql) por FastAPI con psycopg2 connection pool.

**Archivos a crear:** api/main.py, api/db.py, api/geocoder.py, api/requirements.txt, Dockerfile

**Endpoints:** GET /reverse, GET /search, GET /health

**Criterio de aceptación:** \`curl http://100.75.222.2:7171/reverse?lat=10.4806&lon=-66.9036\` devuelve display_name con fuente f58 o nominatim."
```

- [ ] **Step 5: Crear issue #3 — docker-compose + .env.example**

```bash
gh issue create \
  --repo fusion58/search58 \
  --title "feat(infra): docker-compose.yml completo + .env.example" \
  --body "Completar \`infra/docker-compose.yml\` con los servicios \`postgres\` (postgis/postgis:17-3.5) y \`search58-api\` (imagen propia). Crear \`.env.example\` con todas las variables.

**Bind mounts:** \`/opt/search58/postgres\` → datos PostgreSQL

**Criterio de aceptación:** \`docker compose --env-file .env -f infra/docker-compose.yml up -d\` levanta ambos contenedores sin errores."
```

- [ ] **Step 6: Crear issue #4 — Integración Traccar/Route58**

```bash
gh issue create \
  --repo fusion58/search58 \
  --title "config(traccar): apuntar geocoder.url a Search58 QA" \
  --body "Cambiar la configuración de Traccar en Route58 para usar Search58 como geocodificador.

\`\`\`xml
<!-- traccar.xml -->
<entry key='geocoder.type'>nominatim</entry>
<entry key='geocoder.url'>http://100.75.222.2:7171</entry>
\`\`\`

**Prerequisito:** Issues #1, #2 y #3 cerrados y validados.
**Criterio de aceptación:** Un punto GPS en Traccar/Route58 muestra dirección proveniente de Search58."
```

- [ ] **Step 7: Verificar los 4 issues**

```bash
gh issue list --repo fusion58/search58
```

Esperado: 4 issues abiertos numerados #1, #2, #3, #4.

---

## Task 2: api/ — FastAPI con psycopg2 pool

**Files:**
- Crear: `api/requirements.txt`
- Crear: `api/db.py`
- Crear: `api/geocoder.py`
- Crear: `api/main.py`

**Interfaces:**
- Consume: variables de entorno `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `NOMINATIM_URL`, `NOMINATIM_TIMEOUT`, `HYBRID_THRESHOLD`
- Produce: FastAPI app en `main.app`; funciones `geocode_hybrid(lat, lon) -> dict`, `search_places(q, limit) -> list`; `run_sql(sql, params=()) -> list[tuple]`

- [ ] **Step 1: Crear rama de trabajo**

```bash
git checkout -b feat/#2-fastapi
```

- [ ] **Step 2: Crear api/requirements.txt**

Contenido exacto:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg2-binary==2.9.9
httpx==0.27.2
```

- [ ] **Step 3: Crear api/db.py**

```python
import os
import psycopg2
from psycopg2 import pool

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.environ.get('POSTGRES_HOST', 'postgres'),
            port=int(os.environ.get('POSTGRES_PORT', '5432')),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ['POSTGRES_PASSWORD'],
            dbname=os.environ.get('POSTGRES_DB', 'buscador'),
        )
    return _pool

def run_sql(sql, params=()):
    p = get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)
```

- [ ] **Step 4: Crear api/geocoder.py**

```python
import os
import httpx
from db import run_sql

NOMINATIM_URL     = os.environ.get('NOMINATIM_URL',     'https://nominatim.openstreetmap.org')
NOMINATIM_TIMEOUT = int(os.environ.get('NOMINATIM_TIMEOUT', '5'))
HYBRID_THRESHOLD  = int(os.environ.get('HYBRID_THRESHOLD',  '13'))


def score_address(addr: dict) -> int:
    if not addr:
        return 0
    s = 0
    if addr.get('road'):                                 s += 10
    if addr.get('neighbourhood') or addr.get('suburb'):  s += 5
    if addr.get('city'):                                 s += 3
    if addr.get('county'):                               s += 2
    if addr.get('state'):                                s += 2
    if addr.get('country'):                              s += 1
    return s


def geocode_f58(lat: float, lon: float) -> dict:
    sql = (
        "SELECT fulladdress, shortaddress, "
        "nameurbanroads, nametownroads, nameorder9area, nameorder8area, "
        "nameorder2area, denominationorder2area, "
        "nameorder1area, denominationorder1area, namecountry "
        "FROM buscador.f_geocodificacion_inversa("
        "ST_SetSRID(ST_MakePoint(%s, %s), 4326));"
    )
    rows = run_sql(sql, (lon, lat))
    if not rows or not rows[0][0]:
        return {'display_name': 'Sin información', 'address': {}}

    (fulladdress, shortaddress,
     nameurbanroads, nametownroads,
     nameorder9area, nameorder8area,
     nameorder2area, denomorder2,
     nameorder1area, denomorder1,
     namecountry) = rows[0]

    road   = nameurbanroads or nametownroads or ''
    suburb = nameorder9area or ''
    city   = nameorder8area or ''
    county = (f'{denomorder2} {nameorder2area}'.strip()) if nameorder2area else ''
    state  = (f'{denomorder1} {nameorder1area}'.strip()) if nameorder1area else ''

    country_lower = (namecountry or '').lower()
    if 'venezuel'  in country_lower: cc = 've'
    elif 'méxico'  in country_lower or 'mexico' in country_lower: cc = 'mx'
    elif 'guatemal' in country_lower: cc = 'gt'
    else: cc = ''

    return {
        'display_name': fulladdress or shortaddress or 'Sin información',
        'lat': str(lat),
        'lon': str(lon),
        'source': 'f58',
        'address': {
            'road':          road,
            'neighbourhood': suburb,
            'city':          city,
            'county':        county,
            'state':         state,
            'country':       namecountry or '',
            'country_code':  cc,
        },
    }


def geocode_nominatim(lat: float, lon: float) -> dict | None:
    url = (f'{NOMINATIM_URL}/reverse'
           f'?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=es')
    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT,
                          headers={'User-Agent': 'Search58/1.0 (geocoding proxy)'}) as client:
            resp = client.get(url)
            data = resp.json()
    except Exception:
        return None

    a = data.get('address', {})
    return {
        'display_name': data.get('display_name', ''),
        'lat': data.get('lat', str(lat)),
        'lon': data.get('lon', str(lon)),
        'source': 'nominatim',
        'address': {
            'road':          a.get('road') or a.get('pedestrian') or a.get('footway') or '',
            'neighbourhood': a.get('suburb') or a.get('neighbourhood') or a.get('quarter') or '',
            'city':          a.get('city') or a.get('town') or a.get('village') or '',
            'county':        a.get('county') or '',
            'state':         a.get('state') or '',
            'country':       a.get('country') or '',
            'country_code':  a.get('country_code') or '',
        },
    }


def geocode_hybrid(lat: float, lon: float) -> dict:
    f58 = geocode_f58(lat, lon)
    f58_score = score_address(f58.get('address', {}))
    f58['score'] = f58_score

    if f58_score >= HYBRID_THRESHOLD:
        return f58

    nom = geocode_nominatim(lat, lon)
    if nom:
        nom_score = score_address(nom.get('address', {}))
        nom['score']     = nom_score
        nom['f58_score'] = f58_score
        if nom_score > f58_score:
            return nom

    return f58


def search_places(q: str, limit: int = 10) -> list:
    sql = (
        "SELECT nombre, ubicacion, tipo, px, py, "
        "x_min, y_min, x_max, y_max "
        "FROM buscador.f_search_in_country(%s, 862, %s);"
    )
    rows = run_sql(sql, (q, limit))
    results = []
    for row in rows:
        nombre, ubicacion, tipo, px, py, x_min, y_min, x_max, y_max = row
        if px is None or py is None:
            continue
        results.append({
            'display_name': ubicacion or nombre,
            'name':         nombre,
            'lat':          str(py),
            'lon':          str(px),
            'boundingbox':  [str(y_min), str(y_max), str(x_min), str(x_max)],
            'type':         tipo or 'place',
            'class':        'place',
            'source':       'f58',
        })
    return results
```

- [ ] **Step 5: Crear api/main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geocoder import geocode_hybrid, search_places
from db import run_sql, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()   # inicializar el pool al arrancar
    yield


app = FastAPI(title='Search58', version='1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    try:
        run_sql('SELECT 1')
        return {'status': 'ok', 'db': 'connected'}
    except Exception as e:
        raise HTTPException(status_code=503, detail={'status': 'error', 'db': str(e)})


@app.get('/reverse')
def reverse(
    lat: float = Query(..., description='Latitud WGS84'),
    lon: float = Query(..., description='Longitud WGS84'),
):
    return geocode_hybrid(lat, lon)


@app.get('/search')
def search(
    q:     str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    return search_places(q, limit)
```

- [ ] **Step 6: Verificar manualmente (sin servidor activo, solo import)**

```bash
cd D:\Docker\search58
python -c "import ast, pathlib; [ast.parse(f.read_text(encoding='utf-8')) for f in pathlib.Path('api').glob('*.py')]; print('Syntax OK')"
```

Esperado: `Syntax OK`

- [ ] **Step 7: Commit**

```bash
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  add api/
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  commit -m "feat(api): FastAPI con psycopg2 pool — /reverse, /search, /health

Refs #2"
```

---

## Task 3: Dockerfile

**Files:**
- Crear: `Dockerfile` (raíz del repo)

**Interfaces:**
- Consume: `api/requirements.txt`, directorio `api/`
- Produce: imagen `search58-api` que arranca `uvicorn main:app --host 0.0.0.0 --port 7171`

- [ ] **Step 1: Crear Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ .

EXPOSE 7171

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7171", "--workers", "2"]
```

- [ ] **Step 2: Build local para verificar que no hay errores de dependencias**

```bash
cd D:\Docker\search58
docker build -t search58-api:1.0 .
```

Esperado: `Successfully built ...` y `Successfully tagged search58-api:1.0`.

- [ ] **Step 3: Smoke test del contenedor (sin BD, solo que arranca)**

```bash
docker run --rm -e POSTGRES_PASSWORD=dummy -p 7272:7171 search58-api:1.0 &
# esperar 3 segundos y probar
timeout 3 && curl -s http://localhost:7272/health || true
docker stop $(docker ps -q --filter ancestor=search58-api:1.0) 2>/dev/null || true
```

Esperado: o bien `{"detail":{"status":"error","db":"..."}}` (503, no hay BD) o un error de conexión — lo importante es que el proceso arrancó y respondió HTTP.

- [ ] **Step 4: Commit**

```bash
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  add Dockerfile
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  commit -m "feat(api): Dockerfile para search58-api (python:3.12-slim)

Refs #2"
```

---

## Task 4: infra/docker-compose.yml + .env.example

**Files:**
- Modificar: `infra/docker-compose.yml`
- Crear: `.env.example`

**Interfaces:**
- Consume: imagen `search58-api:1.0` (Task 3); variables de `.env`
- Produce: stack `docker compose up` que levanta `postgres` y `search58-api`

- [ ] **Step 1: Reemplazar infra/docker-compose.yml**

Contenido completo:
```yaml
# Search58 — stack QA/prod
# Deploy: docker compose --env-file .env -f infra/docker-compose.yml up -d
# Datos en /opt/search58/ (bind mounts, fuera del contenedor)

services:

  postgres:
    image: postgis/postgis:17-3.5
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${POSTGRES_DB:-buscador}
      POSTGRES_USER:     postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /opt/search58/postgres:/var/lib/postgresql/data
    networks:
      - search58
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d $${POSTGRES_DB:-buscador}"]
      interval: 10s
      timeout: 5s
      retries: 5

  search58-api:
    image: search58-api:1.0
    restart: unless-stopped
    environment:
      POSTGRES_HOST:     postgres
      POSTGRES_PORT:     5432
      POSTGRES_USER:     postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB:       ${POSTGRES_DB:-buscador}
      NOMINATIM_URL:     ${NOMINATIM_URL:-https://nominatim.openstreetmap.org}
      NOMINATIM_TIMEOUT: ${NOMINATIM_TIMEOUT:-5}
      HYBRID_THRESHOLD:  ${HYBRID_THRESHOLD:-13}
    ports:
      - "${SEARCH58_PORT:-7171}:7171"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - search58

networks:
  search58:
    name: search58
```

- [ ] **Step 2: Crear .env.example**

```bash
# Search58 — variables de entorno
# Copiar como .env y completar los secretos (chmod 600 .env)

POSTGRES_PASSWORD=<cambiar>
POSTGRES_DB=buscador

NOMINATIM_URL=https://nominatim.openstreetmap.org
NOMINATIM_TIMEOUT=5
HYBRID_THRESHOLD=13

# Puerto en el que la API queda expuesta hacia Tailscale / localhost
SEARCH58_PORT=7171
```

- [ ] **Step 3: Verificar que el compose es válido localmente**

```bash
docker compose --env-file /dev/null -f infra/docker-compose.yml config
```

> En Windows sin /dev/null: crear un `.env.tmp` vacío y usarlo.

```powershell
New-Item -ItemType File -Path .env.tmp -Force
docker compose --env-file .env.tmp -f infra/docker-compose.yml config
Remove-Item .env.tmp
```

Esperado: YAML expandido sin errores de sintaxis.

- [ ] **Step 4: Actualizar VINCULACIONES.md**

En `## Versiones de imágenes` añadir:
```
- postgis/postgis:17-3.5 — BD Search58 (compose infra/docker-compose.yml)
- search58-api:1.0 — API FastAPI (Dockerfile raíz)
  Al subir versión: actualizar Dockerfile/compose, rebuild en QA, validar /health antes de reiniciar search58-api.
```

- [ ] **Step 5: Actualizar docs/MODIFICACIONES.md**

Reemplazar la sección `## Arranque QA (pendiente — issue #1)` con:
```markdown
## Stack QA — issues #2 y #3

- **Qué:** dos contenedores Docker en red `search58`: `postgres` (postgis/postgis:17-3.5) y `search58-api` (imagen propia Python/FastAPI).
- **Por qué:** eliminar subprocess psql del dev server → 50–200 req/s vs 4 req/s.
- **Datos:** bind mount `/opt/search58/postgres` → `/var/lib/postgresql/data` en el contenedor postgres.
- **Cómo revertir:** `docker compose --env-file .env -f infra/docker-compose.yml down`; datos persisten en `/opt/search58/postgres`.
```

- [ ] **Step 6: Commit**

```bash
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  add infra/docker-compose.yml .env.example VINCULACIONES.md docs/MODIFICACIONES.md
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  commit -m "feat(infra): docker-compose.yml completo + .env.example

Postgres postgis:17-3.5 + search58-api:1.0, healthcheck, bind mount /opt/search58/postgres.

Closes #3"
```

- [ ] **Step 7: Abrir PR y cerrar issue #2**

```bash
git push -u origin feat/#2-fastapi
gh pr create \
  --repo fusion58/search58 \
  --title "feat: FastAPI + Dockerfile + docker-compose QA" \
  --body "$(cat <<'EOF'
## Resumen

- `api/` — FastAPI con psycopg2 pool: /reverse (híbrido F58+Nominatim), /search, /health
- `Dockerfile` — imagen python:3.12-slim, uvicorn 2 workers
- `infra/docker-compose.yml` — postgres (postgis:17-3.5) + search58-api, healthcheck
- `.env.example` — plantilla de variables

## Mejora de rendimiento esperada

| Métrica | Dev server | FastAPI |
|---|---|---|
| Latencia F58 | ~2200 ms (subprocess) | 30–100 ms (psycopg2 pool) |
| Throughput | 4 req/s | 50–200 req/s |

## Plan de prueba

- [ ] `docker build -t search58-api:1.0 .` sin errores
- [ ] `/health` responde `{"status":"ok"}` con BD activa
- [ ] `/reverse?lat=10.4806&lon=-66.9036` devuelve dirección Caracas con `source: f58`
- [ ] `/search?q=Altamira` devuelve resultados

Closes #2, Closes #3
EOF
)"
```

---

## Task 5: Migrar BD buscador al servidor QA

> **Prerequisito:** Issues #2 y #3 mergeados a `main`. Este task es un proceso de deploy; no genera commit de código.

**Files:**
- (sin archivos de código; operación de datos)

**Interfaces:**
- Consume: `~/.ssh/vps_qa`, servidor `root@100.75.222.2`, `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe`
- Produce: BD `buscador` con esquema `buscador` y extensiones PostGIS restaurada en QA bajo `/opt/search58/postgres`

- [ ] **Step 1: Preparar directorios en QA**

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  mkdir -p /opt/search58/postgres /opt/search58/infra
  chmod 700 /opt/search58
  echo 'Directorios OK'
"
```

Esperado: `Directorios OK`

- [ ] **Step 2: Copiar archivos del repo a QA**

```bash
scp -i ~/.ssh/vps_qa \
  infra/docker-compose.yml \
  root@100.75.222.2:/opt/search58/infra/docker-compose.yml

scp -i ~/.ssh/vps_qa \
  .env.example \
  root@100.75.222.2:/opt/search58/.env.example
```

- [ ] **Step 3: Crear .env en QA con la contraseña real**

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  cp /opt/search58/.env.example /opt/search58/.env
  sed -i 's/<cambiar>/casa1234/' /opt/search58/.env
  chmod 600 /opt/search58/.env
  cat /opt/search58/.env
"
```

Esperado: archivo `.env` con `POSTGRES_PASSWORD=casa1234` y las demás variables.

- [ ] **Step 4: Construir la imagen en QA**

Primero copiar el código de la API y el Dockerfile a QA:

```bash
scp -i ~/.ssh/vps_qa -r api/ root@100.75.222.2:/opt/search58/api/
scp -i ~/.ssh/vps_qa Dockerfile root@100.75.222.2:/opt/search58/Dockerfile
```

Luego hacer el build en QA:
```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  cd /opt/search58
  docker build -t search58-api:1.0 .
  echo 'Build OK'
"
```

Esperado: `Build OK` y `search58-api:1.0` en `docker images`.

- [ ] **Step 5: Levantar solo el contenedor postgres**

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  docker compose --env-file /opt/search58/.env \
    -f /opt/search58/infra/docker-compose.yml \
    up -d postgres
"
```

Esperar ~10 segundos y verificar que está sano:

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "docker ps | grep postgres"
```

Esperado: `healthy` en la columna STATUS.

- [ ] **Step 6: Hacer pg_dump del esquema buscador (solo esquema buscador)**

Desde el equipo local (Windows). Usar pg_dump 18 para evitar el mismatch de versiones:

```powershell
$env:PGPASSWORD = 'casa1234'
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
  -h localhost -p 5433 -U postgres `
  --schema=buscador `
  --no-owner --no-acl `
  -Fc buscador `
  -f "$env:TEMP\buscador_schema.dump"
Write-Host "Tamaño del dump: $((Get-Item $env:TEMP\buscador_schema.dump).Length / 1MB) MB"
```

Esperado: archivo `buscador_schema.dump` en `$TEMP`, tamaño entre 300–800 MB (comprimido).

> **Si el dump falla por versión:** añadir la flag `--no-sync` o usar formato plain (`-Fp`) y referenciar el archivo como `.sql`.

- [ ] **Step 7: Transferir el dump a QA**

```bash
scp -i ~/.ssh/vps_qa "$env:TEMP\buscador_schema.dump" root@100.75.222.2:/opt/search58/buscador_schema.dump
```

Esperar — serán ~300–800 MB. Puede tardar 2–10 minutos dependiendo del ancho de banda.

- [ ] **Step 8: Restaurar en el contenedor postgres de QA**

Obtener el nombre del contenedor postgres:
```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "docker ps --filter name=postgres --format '{{.Names}}'"
```

Luego restaurar (reemplazar `search58-postgres-1` con el nombre real):
```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  docker exec -i search58-postgres-1 \
    pg_restore -U postgres -d buscador \
    --no-owner --no-acl \
    < /opt/search58/buscador_schema.dump
  echo 'Restore completado: código $?'
"
```

Esperado: mensajes de restauración (pueden aparecer algunos warnings de secuencias o permisos — normales). El código de salida debe ser `0`.

- [ ] **Step 9: Verificar que las funciones clave existen en QA**

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  docker exec search58-postgres-1 \
    psql -U postgres -d buscador -t -A \
    -c \"SELECT proname FROM pg_proc p JOIN pg_namespace n ON p.pronamespace=n.oid WHERE n.nspname='buscador' ORDER BY proname LIMIT 10\"
"
```

Esperado: lista con `f_geocodificacion_inversa`, `f_search_in_country`, etc.

---

## Task 6: Deploy completo y validación en QA

> **Prerequisito:** Task 5 completado (BD restaurada, imagen construida en QA).

**Files:**
- Modificar: `ESTADO_SESION.md`

**Interfaces:**
- Consume: contenedor `search58-postgres-1` corriendo con BD buscador; imagen `search58-api:1.0` en QA
- Produce: stack completo funcionando; `/health`, `/reverse` y `/search` respondiendo en `100.75.222.2:7171`

- [ ] **Step 1: Levantar el stack completo**

```bash
ssh -i ~/.ssh/vps_qa root@100.75.222.2 "
  docker compose --env-file /opt/search58/.env \
    -f /opt/search58/infra/docker-compose.yml \
    up -d
  docker compose --env-file /opt/search58/.env \
    -f /opt/search58/infra/docker-compose.yml \
    ps
"
```

Esperado: ambos servicios `running (healthy)`.

- [ ] **Step 2: Validar /health**

```bash
curl -s http://100.75.222.2:7171/health
```

Esperado:
```json
{"status":"ok","db":"connected"}
```

- [ ] **Step 3: Validar /reverse con punto en Caracas**

```bash
curl -s "http://100.75.222.2:7171/reverse?lat=10.4806&lon=-66.9036" | python -m json.tool
```

Esperado: JSON con `display_name` conteniendo dirección de Caracas, `source: "f58"`, `score` ≥ 13.

- [ ] **Step 4: Validar /reverse con punto rural (debe usar Nominatim)**

Usar un punto en el Amazonas venezolano (zona sin datos F58):
```bash
curl -s "http://100.75.222.2:7171/reverse?lat=4.0&lon=-66.0" | python -m json.tool
```

Esperado: JSON con `source: "f58"` (score bajo) o `source: "nominatim"` si Nominatim tiene mejor score. No debe devolver error.

- [ ] **Step 5: Validar /search**

```bash
curl -s "http://100.75.222.2:7171/search?q=Altamira&limit=5" | python -m json.tool
```

Esperado: array JSON con al menos 1 resultado con `source: "f58"`.

- [ ] **Step 6: Prueba de latencia (comparación vs dev server)**

```bash
# 5 peticiones consecutivas a Caracas
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "%{time_total}s\n" \
    "http://100.75.222.2:7171/reverse?lat=10.4806&lon=-66.9036"
done
```

Esperado: tiempos < 200 ms (vs ~2200 ms del dev server). Si el primer request es lento (cold start del pool), los siguientes deben ser rápidos.

- [ ] **Step 7: Actualizar ESTADO_SESION.md**

Añadir al principio del archivo:
```markdown
## 2026-08-07 — Arranque QA completado

- **Stack en QA:** postgres (postgis:17-3.5) + search58-api:1.0 en Docker, servidor 100.75.222.2:7171.
- **BD migrada:** esquema `buscador` desde localhost:5433 — funciones f_geocodificacion_inversa, f_search_in_country + datos Venezuela.
- **Issues cerrados:** #2 (FastAPI), #3 (compose).
- **Issues abiertos:** #1 (Closes tras merge del PR), #4 (integración Traccar — pendiente).
- **Próximo paso:** apuntar Traccar/Route58 a http://100.75.222.2:7171 (issue #4).
```

- [ ] **Step 8: Commit final**

```bash
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  add ESTADO_SESION.md
git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' \
  commit -m "docs(sesion): arranque QA completado — stack validado en 100.75.222.2

Closes #1"
```

---

## Notas de implementación

### Versión de pg_dump
El servidor local es PostgreSQL 18.4; el pg_dump en PATH es la versión 14.3. Usar siempre `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe` para el dump. Si falla, alternativa: format plain (`-Fp`) que genera SQL puro compatible con cualquier versión.

### Schemas omitidos en el dump
El dump cubre solo el esquema `buscador` (funciones + datos Venezuela). Los esquemas `source`, `backup`, `busquedas`, `geoip`, etc. no se migran a QA para reducir el tamaño (~1 GB vs ~3.8 GB del dump completo).

### Puerto postgres en QA
El contenedor postgres **no expone puerto** al host QA (solo en la red Docker interna `search58`). Para consultas de diagnóstico desde fuera, usar `docker exec search58-postgres-1 psql ...`.

### Contraseña postgres en QA
Para este entorno QA, la contraseña es `casa1234` (igual que local). En producción, usar una contraseña generada y rotarla por Vault/secret manager.
