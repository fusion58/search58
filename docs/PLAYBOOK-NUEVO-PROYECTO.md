# Playbook — Arrancar un proyecto nuevo en QA (Fusión58)

> Guía práctica destilada de la experiencia real montando **ServiceMap/GeoServer** en QA.
> Objetivo: que arrancar un servicio nuevo (ej. **OSRM**) sea rápido, correcto y sin sorpresas,
> siguiendo el manual Fusión58 pero con los atajos ya aprendidos.
>
> **Cómo usar este archivo:** cópialo a la raíz del proyecto nuevo (ej. `docs/` del repo de OSRM).
> Cuando abras Claude CLI en ese directorio, léelo junto al `CLAUDE.md` y sabrás exactamente qué hacer.

---

## 0. TL;DR — el flujo en una línea

**Issue → rama → cambios → validar (visual + datos) → PR → merge a `main` (con tu OK) → deploy a QA → validación end-to-end → cerrar issue.**
Datos siempre **fuera de Docker** en `/opt/<proyecto>/`. Nunca `latest`, siempre versión fija. Backup antes de tocar algo productivo.

---

## 1. Estructura estándar del repo

Todo proyecto arranca con esta forma (crea lo que aplique):

```
<proyecto>/
├── CLAUDE.md              ← directivas que Claude carga solo (plantilla en §3)
├── README.md             ← qué es, cómo se levanta
├── CONTRIBUTING.md       ← resumen operativo para colaboradores
├── VINCULACIONES.md      ← mapa anti-deriva "si cambias X → actualiza Y"
├── CHANGELOG.md          ← versiones (SemVer)
├── ESTADO_SESION.md      ← bitácora viva (lo más reciente arriba)
├── .env.example          ← variables con PLACEHOLDERS (nunca secretos reales)
├── .gitignore            ← .env, *.bak.*, desktop.ini, node_modules/
├── .claude/
│   └── settings.local.json   ← permisos pre-aprobados (§4)
├── docs/
│   ├── MODIFICACIONES.md     ← qué difiere de la base vainilla (qué, por qué, dónde, cómo revertir)
│   └── PLAYBOOK-NUEVO-PROYECTO.md  ← este archivo
├── infra/
│   └── docker-compose.yml    ← el stack (datos por bind mount a /opt/<proyecto>)
└── .github/
    └── ISSUE_TEMPLATE/        ← feature, bug, config-change, research
```

---

## 2. Reglas de oro (no negociables)

1. **Issue antes de tocar nada operativo** (código, config, infra, BD, proxy, DNS). El commit lo cierra con `Closes #N`.
2. **Un cambio no está "listo" hasta verlo funcionar** en el cliente real (visual + datos), no porque "responde 200" o "compila". Hasta validar: `Refs #N`, no `Closes`.
3. **Datos fuera de las imágenes**, en `/opt/<proyecto>/` (bind mounts). Sobreviven a recreaciones. Todo path nuevo → al backup.
4. **Versiones fijas** de imágenes (nunca `latest`). Para congelar exacto: pin por digest `@sha256:...`.
5. **Secretos nunca** en el repo ni en el chat. Solo `.env.example` con placeholders; los valores reales viven en el `.env` del server (chmod 600) o en Vaultwarden.
6. **Backup antes de cualquier cambio productivo:** `cp file file.bak.<timestamp>` o `tar -czf ...`.
7. **QA es espejo de prod.** La misma imagen validada en QA es la que va a prod. Los datos nunca se tocan al promover.

---

## 3. Plantilla de `CLAUDE.md` (rellena los `<...>` y cópiala a la raíz)

```markdown
<Producto> es <descripción>. Producción: https://<dominio-prod> QA: acceso por Tailscale (puerto directo; dominio QA por definir). Repo: https://github.com/fusion58/<repo> (branch default main).

## Idioma
- Español de Venezuela, tuteo. Nunca voseo. "carro", "cuadra".
- Aplica a chat, docs, UI, commits, títulos de PR, issues. Excepción: comentarios de código técnico.
- Siglas: primera vez sigla + forma desarrollada, ej. `OSRM (Open Source Routing Machine)`.
- No refieras issues/PRs solo por número; siempre `#N` + descripción corta.

## Identidad git
- Nombre: <Tu Nombre> · Correo: <tu-correo>
- Pásala por comando sin tocar el config global:
  `git -c user.email='<correo>' -c user.name='<nombre>' commit -m "..."`

## Flujo
- Issue-first. Rama `feat|fix|config|docs|hotfix/<N>-<slug>`. PR a `main`, nunca push directo.
- Conventional commits en español: `feat(scope): ...`, `config(infra): ...`.
- `Closes #N, Closes #M` (keyword repetida) para cerrar varios.
- Validación visual end-to-end antes de cerrar. Hasta entonces `Refs #N`.

## Infra QA
- Server QA: `root@<ip-tailscale>` (por Tailscale). Llave SSH: `~/.ssh/<llave>`.
- Datos en `/opt/<proyecto>/` (bind mounts). Compose en `infra/`.
- Comando de deploy: `docker compose --env-file .env -f infra/docker-compose.yml up -d`
  (¡el `--env-file` es obligatorio! Ver §5 del playbook).
- Las BD no publican puerto al host; se acceden por túnel SSH o pgAdmin del box.

## Autonomía (ver §4 del playbook)
- Puedo hacer SIN preguntar: leer, buscar, editar archivos locales, build/lint/tests,
  levantar stack local, consultar API/logs, abrir issues/PRs, inspeccionar el server (solo lectura).
- Requiere tu OK explícito: deploy/recreate en QA/prod, cambios en server/proxy/DNS/certificados,
  push a `main`, merge de PR, cambios de BD productiva, tocar secretos.
- Autorización "de una": si me dices "tienes permiso para todo en este issue", ejecuto el issue
  completo (con backups) sin volver a preguntar por cada paso; solo me detengo en la validación final.

## Excepciones de este proyecto
- _(ninguna por ahora)_
```

---

## 4. No pedir autorización a cada rato — dos niveles

Hay **dos tipos** de "autorización" y se resuelven distinto:

### A) Prompts técnicos de Claude Code ("¿Permito este comando?")
Se reducen con `.claude/settings.local.json`. Pre-aprueba los comandos **seguros y de lectura**.
Copia esto (ajusta a tu stack):

```json
{
  "permissions": {
    "allow": [
      "Read", "Grep", "Glob", "Edit", "Write",
      "Bash(git status:*)", "Bash(git log:*)", "Bash(git diff:*)", "Bash(git branch:*)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git checkout:*)", "Bash(git pull:*)",
      "Bash(docker ps:*)", "Bash(docker inspect:*)", "Bash(docker logs:*)",
      "Bash(docker images:*)", "Bash(docker compose config:*)",
      "Bash(gh issue list:*)", "Bash(gh issue view:*)", "Bash(gh pr list:*)",
      "Bash(gh pr view:*)", "Bash(gh label list:*)",
      "Bash(ls:*)", "Bash(cat:*)", "Bash(du:*)", "Bash(df:*)", "Bash(curl:*)",
      "PowerShell(docker ps*)", "PowerShell(docker inspect*)", "PowerShell(Get-ChildItem*)",
      "PowerShell(Test-Path*)", "PowerShell(Get-NetTCPConnection*)"
    ],
    "deny": []
  }
}
```

**Qué NO poner en `allow`** (que sigan preguntando, por seguridad — son los productivos/destructivos):
`docker compose up/down`, `docker rm`, `git push`, `gh pr merge`, `gh repo create`, `rm -rf`,
y **`ssh`** (porque un `ssh` puede cambiar el server; que te lo pregunte).

> Si de verdad quieres cero fricción en tu propio box QA, puedes agregar `"Bash(ssh:*)"` al `allow`
> — pero entiende que eso me deja correr **cualquier** cosa en el server sin preguntarte. Trade-off tuyo.

### B) Autorización del dueño (regla de negocio del manual)
Esto **no** es un prompt técnico: es la regla de que **lo productivo requiere tu OK**. Para no ir
pregunta-por-pregunta, la convención práctica que ya usamos:

- **"tienes permiso para todo en este issue"** → ejecuto el issue completo de corrido (con backups),
  y solo me detengo al final para tu **validación visual**.
- Sin esa frase, te pido OK antes de cada acción que toca QA/prod/server.

Resumen: **settings.local.json** quita los prompts técnicos de lo seguro; la **frase de permiso por issue**
quita las preguntas de negocio. Juntas = fluido, sin perder el control de lo importante.

---

## 5. Patrón de deploy a QA (probado, con sus gotchas)

1. **Acceso:** `ssh -i ~/.ssh/<llave> root@<ip-tailscale>` (Tailscale encendido). Verifica `docker --version`.
2. **Estructura en el server:**
   ```
   /opt/<proyecto>/
   ├── infra/docker-compose.yml
   ├── .env            (valores reales, chmod 600)
   └── <datos>/        (bind mounts: db, media, etc.)
   ```
3. **Secretos:** genéralos EN el server (`openssl rand -hex 24`), nunca por el chat.
4. **Levantar:** desde `/opt/<proyecto>/`:
   ```bash
   docker compose --env-file .env -f infra/docker-compose.yml up -d
   ```
5. **Validar:** contenedores healthy + prueba end-to-end real (no solo un 200).

### ⚠️ Gotchas que YA nos mordieron (no repetir)

| Gotcha | Solución |
|---|---|
| **`--env-file` obligatorio.** Con `-f infra/…`, Compose busca el `.env` en `infra/`, no en la raíz → variables en blanco (¡Postgres sin clave, binds a `/`!). | Siempre `--env-file .env`. |
| **Bind a Tailscale.** Para exponer solo al tailnet: `"${IP_TAILSCALE}:${PUERTO}:<interno>"`. | Panel admin (pgAdmin, etc.) déjalo en `127.0.0.1` y accédelo por **túnel SSH**. |
| **Servicio en `localhost` del server** no se alcanza desde tu PC aunque estés en Tailscale. | Túnel: `ssh -L <local>:127.0.0.1:<remoto> root@<ip>`; abre `http://127.0.0.1:<local>`. |
| **Puerto local ocupado** (ej. 5050 por WSL). | Usa otro puerto local en el `-L` (ej. `5056:127.0.0.1:5050`). |
| **Transferir data grande** sin rsync en Windows. | `tar -cf - -C <src> . | ssh <host> "tar -xf - -C <dst>"` (streaming). |
| **`pg_restore` desde stdin** falla con tablas particionadas. | Restaura **desde archivo** (transfiere el `.dump` y `pg_restore /ruta/archivo`). |
| **Particiones con `DEFAULT nextval()` de otro esquema** → CREATE falla, 0 datos. | Pre-crear ese esquema + las secuencias vacías antes del restore. |
| **Sandbox bloquea `Move-Item` a rutas raíz nuevas** en Windows. | Usa `.NET`: `[System.IO.Directory]::Move(src,dst)`. |
| **`gh` no instalado.** | Descarga el zip de releases de `cli/cli`, agrégalo al PATH, `gh auth login` (navegador). |
| **Git identidad:** usa `-c user.email=... -c user.name=...` por comando, no el global. | — |
| **Credencial de push:** token de `gh` efímero como helper, no lo guardes en `.git/config`. | — |

---

## 6. OSRM — específico (arranque en QA)

**Qué es:** OSRM (Open Source Routing Machine) — motor de ruteo. Sirve una API HTTP de rutas
(por defecto puerto `5000`) a partir de datos OSM preprocesados.

**Lo que implica (no es solo `up -d`):** OSRM necesita **preprocesar** un extracto OSM antes de servir.

### Flujo de datos (algoritmo MLD, recomendado)
1. **Bajar el extracto OSM** (ej. Venezuela de Geofabrik): `venezuela-latest.osm.pbf`.
2. **Extraer:** `osrm-extract -p /opt/car.lua /data/venezuela-latest.osm.pbf`
3. **Particionar:** `osrm-partition /data/venezuela-latest.osrm`
4. **Customizar:** `osrm-customize /data/venezuela-latest.osrm`
5. **Servir:** `osrm-routed --algorithm mld /data/venezuela-latest.osrm` → API en `:5000`

Los pasos 2-4 se corren **una vez** (o cuando actualizas el mapa); el 5 es el servicio permanente.

### Estructura sugerida en QA
```
/opt/osrm/
├── infra/docker-compose.yml
├── .env
└── data/                     ← .osm.pbf + .osrm (bind mount a /data)
```
- Imagen fija: `osrm/osrm-backend:<versión>` (verifica la última estable; no `latest`).
- `osrm-routed` bind al IP de Tailscale (`${OSRM_BIND}:${OSRM_PORT}:5000`).
- Perfiles disponibles en la imagen: `car.lua`, `bicycle.lua`, `foot.lua` (en `/opt/`).

### Cosas a decidir en el brainstorming (antes de tocar)
- ¿Qué extracto/región? (tamaño de datos, RAM/disco del box — recuerda que el QA tiene ~7.8GB RAM sin swap).
- ¿Algoritmo MLD (customizable rápido) o CH (más rápido en query, preprocesa más lento)?
- ¿Perfil car/bike/foot? ¿Uno o varios servicios?
- ¿Cómo se actualiza el mapa? (job de re-preprocesamiento).

> El preprocesamiento de OSRM puede ser **pesado en RAM** (proporcional al tamaño del extracto).
> Venezuela completo es manejable; regiones grandes pueden no caber en el box QA — evaluar en el issue.

---

## 7. Paso a paso para arrancar OSRM (lo que TÚ haces)

1. **Prepara el directorio** del proyecto OSRM en tu máquina:
   - Copia este `PLAYBOOK-NUEVO-PROYECTO.md` a `docs/`.
   - Crea el `CLAUDE.md` desde la plantilla (§3), rellenando `<Producto>=OSRM`, repo, tu identidad, IP QA, llave SSH.
   - Crea `.claude/settings.local.json` con los permisos (§4).
   - Crea `.gitignore` (`.env`, `*.bak.*`, `data/`, `*.osm.pbf`, `*.osrm*`).
2. **Abre Claude CLI** en ese directorio → cargará el `CLAUDE.md` y reconocerá el contexto.
3. **Dile a Claude:** *"Vamos a arrancar OSRM en QA siguiendo el playbook. Empecemos por el brainstorming."*
4. Claude te hará las preguntas de decisión (§6), abrirá el **issue**, y ejecutará con la estructura estándar.
5. Cuando quieras que ejecute de corrido: *"tienes permiso para todo en este issue"*.
6. Al final, **valida visual/datos** (prueba una ruta real contra la API) → cierras el issue.

---

## 8. El día a día (después del arranque)

- **Cambio nuevo** → issue → rama `config|feat|fix/<N>-<slug>` → cambios → PR → validar → merge (con tu OK).
- **Actualizar el mapa OSM** → issue, re-preprocesar, validar rutas, promover.
- **Conectarte a un panel interno del box** (pgAdmin, etc.) → túnel SSH (§5).
- **Revisar el estado** → "Claude, dame el estado de los contenedores / issues abiertos / qué quedó pendiente".
- **Anti-deriva:** cada cambio que queda funcionando → actualiza `MODIFICACIONES`, `VINCULACIONES`, `ESTADO_SESION` en el mismo trabajo.
- **Promover a prod** → solo desde `main`, con tu aprobación explícita (publicar Release). La misma imagen validada en QA.

---

*Este playbook nació del arranque de ServiceMap/GeoServer. Si en OSRM aprendemos algo nuevo, agrégalo a §5 (gotchas) para el próximo proyecto.*
