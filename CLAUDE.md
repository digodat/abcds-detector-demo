@AGENTS.md

## Recordatorio para features nuevas

Este backend y el front (`~/Documents/dev/abcds-detector-demo-front`) son un solo sistema
repartido en dos repos. Ver la sección "Arquitectura" de `AGENTS.md` antes de estimar o
implementar una feature: si el cambio toca el contrato (`api_models.py`, endpoints de
`server.py`, eventos SSE), el front necesita un cambio espejo y hay que decirlo en el plan.

## GitHub / PRs — nunca contra el upstream de Google

Este repo es el fork `digodat/abcds-detector-demo`. Se dejó de seguir el upstream
`google-marketing-solutions/abcds-detector` de forma consciente (ver `AGENTS.md`).

- **NUNCA** abrir un PR contra `google-marketing-solutions/abcds-detector` ni contra
  ningún otro repo de `google-marketing-solutions/*`.
- Al crear un PR con `gh pr create`, apuntar siempre a `digodat/abcds-detector-demo`
  (usar `--repo digodat/abcds-detector-demo` si hace falta). Verificar que la base sea
  `digodat/...`, no el remote `upstream`.
- El remote `upstream` puede existir localmente por historia del fork; no usarlo para
  PRs ni merges rutinarios. Si `gh` abre un PR cross-repo hacia Google, cerrarlo de
  inmediato y recrearlo contra digodat.
