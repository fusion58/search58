# Vinculaciones — mapa anti-deriva "si cambias X, actualiza Y"

## Infra / compose

- **Servicio nuevo o cambio en `infra/docker-compose.yml`** → actualizar `.env.example`, `docs/MODIFICACIONES.md`, y (a futuro) el workflow de deploy y la promoción a prod.
- **Path nuevo que la app escriba a disco** → agregarlo al backup y mapearlo como bind mount.
- **Puerto o bind cambian** → actualizar `.env.example`, `CLAUDE.md` (sección Infra QA), y docs de acceso.

## Backup / DR

Paths de datos que deben respaldarse en el server QA (completar al definir el stack):

- `/opt/search58/` — directorio raíz de datos (bind mounts del geocodificador y su BD).

## Versiones de imágenes

- `postgis/postgis:17-3.5` — BD Search58 (compose `infra/docker-compose.yml`)
- `search58-api:1.0` — API FastAPI (Dockerfile raíz)
  Al subir versión: actualizar Dockerfile/compose, rebuild en QA (`docker build`), validar `/health` antes de reiniciar `search58-api`.
- Al cambiar `api/*.py` → rebuild imagen → redeploy en QA.

## Acceso / red

- **IP de Tailscale del server** → si cambia, actualizar `.env` del server y `CLAUDE.md` (sección Infra QA).
- **Nombre de la red docker `search58`** → si cambia, actualizar el compose y cualquier servicio conectado a ella.

## Integración con Route58

- **Endpoint de la API de Search58** → si cambia host/puerto, actualizar la config de Traccar en Route58.
- **Formato de respuesta** → coordinar con el equipo de Route58 antes de cambiar el contrato de la API.
