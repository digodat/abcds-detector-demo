@AGENTS.md

## Recordatorio para features nuevas

Este backend y el front (`~/Documents/dev/abcds-detector-demo-front`) son un solo sistema
repartido en dos repos. Ver la sección "Arquitectura" de `AGENTS.md` antes de estimar o
implementar una feature: si el cambio toca el contrato (`api_models.py`, endpoints de
`server.py`, eventos SSE), el front necesita un cambio espejo y hay que decirlo en el plan.
