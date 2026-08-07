# Modificaciones del stack Search58

Registro de lo que diferencia este stack de sus imágenes base vainilla.

> _Este archivo se llena en el mismo trabajo que el primer deploy QA (issue #1)._

## Stack QA — issues #2 y #3

- **Qué:** dos contenedores Docker en red `search58`: `postgres` (postgis/postgis:17-3.5) y `search58-api:1.0` (Python/FastAPI).
- **Por qué:** eliminar el subprocess psql del dev server → 50–200 req/s vs 4 req/s con psycopg2 pool.
- **Datos:** bind mount `/opt/search58/postgres` → `/var/lib/postgresql/data` en el contenedor postgres.
- **Cómo revertir:** `docker compose --env-file .env -f infra/docker-compose.yml down`; datos persisten en `/opt/search58/postgres`.
