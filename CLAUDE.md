Search58 es la API de geocodificación inversa de Fusión58 — bautiza puntos de posición GPS con datos OpenStreetMap para Route58 (Traccar). Producción: https://<dominio-prod> (por definir). QA: acceso por Tailscale (puerto directo; dominio QA por definir). Repo: https://github.com/fusion58/search58 (branch default main).

---

## Idioma y comunicación

- **Español de Venezuela, tuteo.** "tú puedes", "mira", "revisa", "guarda". **Nunca voseo.**
- Aplica a chat, docs, UI, commits, títulos de PR, issues. Excepción: comentarios de código técnico.
- Siglas: primera vez sigla + forma desarrollada: `OSM (OpenStreetMap)`. Después, solo la sigla.
- No refieras issues/PRs solo por número; siempre `#N` + descripción corta.

---

## Identidad git

- Nombre: Angel Pacheco · Correo: angel.pacheco.sigis@gmail.com
- Sin tocar el config global:
  `git -c user.email='angel.pacheco.sigis@gmail.com' -c user.name='Angel Pacheco' commit -m "..."`

---

## Flujo de trabajo

- **Issue-first.** Cualquier cambio operativo requiere issue abierto. El commit lo cierra con `Closes #N`.
- Ramas: `feat/<N>-slug`, `fix/<N>-slug`, `config/<N>-slug`, `docs/<N>-slug`, `hotfix/<N>-slug`.
- PR a `main`, nunca push directo.
- Conventional commits en español: `feat(scope): ...`, `config(infra): ...`, `fix(scope): ...`.
- Cerrar varios issues: `Closes #N, Closes #M` (keyword repetida, no solo espacios).
- Validación visual end-to-end antes de cerrar. Hasta entonces: `Refs #N`.

---

## Infra QA

- Server QA: `root@100.75.222.2` (por Tailscale). Llave SSH: `~/.ssh/<llave-ssh>`.
- Datos en `/opt/search58/` (bind mounts, fuera de Docker). Compose en `infra/`.
- Deploy: `docker compose --env-file .env -f infra/docker-compose.yml up -d`
  (**`--env-file` obligatorio** — sin él las variables quedan en blanco.)
- Los servicios no publican puerto a internet; acceso por Tailscale o túnel SSH.

---

## Autonomía

| Puedes hacer SIN preguntar | Requiere OK explícito del dueño |
|---|---|
| Leer código, buscar, editar archivos locales | Deploy/recreate en QA o prod |
| Build, lint, tests, levantar stack local | Cambios en server/proxy/DNS/certificados |
| Consultar API/logs, abrir issues/PRs | Push a `main`, merge de PR |
| Inspeccionar el server (solo lectura) | Cambios de BD productiva, tocar secretos |

**Autorización "de una":** si el dueño dice "tienes permiso para todo en este issue", ejecuto el issue completo (con backups) sin volver a preguntar; solo me detengo en la validación visual final.

---

## Al iniciar sesión

1. Lee `ESTADO_SESION.md` — bitácora viva (qué se hizo, dónde quedamos, próximos pasos).
2. Lee `docs/MODIFICACIONES.md` — qué diferencia este stack de su base vainilla.
3. Lee `VINCULACIONES.md` — mapa "si cambias X, actualiza Y".
4. No confíes en snapshots de issues; consulta GitHub antes de actuar sobre un issue.

---

## Al completar un cambio

En el mismo trabajo: actualiza `ESTADO_SESION.md`, `docs/MODIFICACIONES.md` y `VINCULACIONES.md`.

---

## Excepciones de este proyecto al estándar Fusión58

- _(ninguna por ahora)_
