# Contribuir a Search58

Resumen operativo (detalle completo en `CLAUDE.md` y `docs/PLAYBOOK-NUEVO-PROYECTO.md`).

- **Issue primero:** todo cambio operativo requiere un issue abierto antes.
- **Ramas:** `feat/<N>-<slug>`, `fix/<N>-<slug>`, `config/<N>-<slug>`, `docs/<N>-<slug>`, `hotfix/<N>-<slug>`. Nunca push directo a `main`.
- **Commits:** convencionales, en español (tuteo). `type(scope): mensaje`. Cierra issues con `Closes #N` en el body (o `Refs #N` hasta validar).
- **Identidad git:** usa tu propio nombre y correo.
- **Secretos:** nunca en el repo. Solo `.env.example` con placeholders.
- **Validación:** un cambio no se cierra hasta verlo funcionar end-to-end (una geocodificación/búsqueda real) + segunda confirmación del dueño.
