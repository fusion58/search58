# Modificaciones del stack Search58

Registro de lo que diferencia este stack de sus imágenes base vainilla.

> _Este archivo se llena en el mismo trabajo que el primer deploy QA (issue #1)._

## Arranque QA (pendiente — issue #1)

- **Qué:** stack inicial del geocodificador inverso (Nominatim u alternativa).
- **Por qué:** bautizar puntos de posición GPS para Route58 (Traccar).
- **Cómo revertir:** `docker compose --env-file .env -f infra/docker-compose.yml down`; los datos quedan en `/opt/search58/`.
