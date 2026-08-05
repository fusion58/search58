# Search58

API de geocodificación inversa para Fusión58. Recibe coordenadas GPS y devuelve la dirección legible correspondiente, para bautizar los puntos de posición de Route58 (Traccar).

## Stack

Por definir en issue #1. Candidatos: Nominatim (OpenStreetMap), Photon.

## QA

Acceso por Tailscale. Deploy:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d
```

## Flujo de trabajo

Ver `CLAUDE.md` y `docs/PLAYBOOK-NUEVO-PROYECTO.md`.
