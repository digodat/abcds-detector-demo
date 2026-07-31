# AGENTS.md

Backend FastAPI de ABCDs Detector. Corre en Cloud Run y expone la evaluación ABCD de
creatividades en video.

> Este archivo y `CLAUDE.md` son locales de este fork (`digodat/abcds-detector-demo`). No
> existen en el upstream `google-marketing-solutions/abcds-detector`.
>
> **Upstream:** se dejó de seguir el upstream de forma consciente. No asumir merges
> periódicos desde `google-marketing-solutions/abcds-detector`; este repo evoluciona por su
> cuenta. Si en el futuro se retoma, tratarlo como un port puntual, no como sync rutinario.

## Arquitectura: este repo es la mitad de un sistema de dos repos

Esta API es consumida por un front Next.js que vive en **otro repositorio del mismo dueño**:

| | Backend (este repo) | Front |
|---|---|---|
| Path local | `~/Documents/dev/abcds-detector-demo` | `~/Documents/dev/abcds-detector-demo-front` |
| GitHub | `digodat/abcds-detector-demo` (fork de `google-marketing-solutions/abcds-detector`) | `digodat/abcds-detector-demo-front` |
| Stack | FastAPI + Python | Next.js (App Router) |
| Deploy | Cloud Run, trigger de GitHub sobre `main` (`cloudbuild.yaml`) | Cloud Run, trigger de GitHub sobre `main` |

**Muchas features requieren tocar los dos repos en el mismo cambio.** Antes de planificar una
feature nueva, evaluar si el front necesita cambios y decirlo explícitamente. Si el repo del
front no está accesible en la sesión, avisar al usuario en vez de dar por cerrada la feature.

### Punto de conexión

- El front llama a esta API vía su env var `ABCD_API_BASE_URL` apuntando al servicio de
  Cloud Run. **Siempre apunta al servicio deployado**, no a un uvicorn local.
- Superficie expuesta (`server.py`): `POST /evaluate`, `POST /evaluate/stream` (SSE),
  `GET /health`. Agregar un endpoint implica cablearlo del lado del front.
- Del lado del front, el cliente vive en `src/lib/abcd-evaluate.ts` (arma el payload) y
  `src/lib/abcd-api.ts` (parsea la respuesta).
- La feature "mejorar prompt" del front llama a Vertex AI directo y **no** pasa por esta API.

### Contrato de tipos (mantener espejado)

| Backend (`api_models.py`) | Front (`src/types/audit.ts`) |
|---|---|
| `EvaluateRequest` | payload de `buildEvaluatePayload()` en `src/lib/abcd-evaluate.ts` |
| `EvaluateResponse` | `ABCDEvaluateResponse` |
| `VideoAssessmentResponse` | `ABCDAssessment` |
| `FeatureEvaluationResponse` | `ABCDFeatureEvaluation` |
| eventos SSE de `/evaluate/stream` | `ABCDStreamEvent` |

Renombrar o borrar un campo en `api_models.py` sin espejarlo rompe el front en runtime, no en
build: no hay validación de schema del otro lado, el campo simplemente llega `undefined`.

**Fuente de verdad del contrato**: `api_models.py` + `docs/api-guide.md` de este repo. Un
cambio de contrato actualiza los dos en el mismo commit.

### Orden de deploy

Los dos servicios deployan por separado y hay una ventana en la que corren versiones
distintas. Usar expand/contract:

- **Cambio aditivo** (campo o endpoint nuevo): deployar este repo primero, después el front.
- **Rename o borrado**: adaptar y deployar el front primero, después limpiar acá.
- Nunca borrar un campo en el mismo push en el que el front deja de usarlo.

### Configuración que vive partida entre repos

- **Timeouts**: acá se deploya con `--timeout=3600` (Cloud Run, en `cloudbuild.yaml`) y el
  front corta a `ABCD_API_TIMEOUT_MS` (default 15 min). Si un cambio hace el análisis más
  lento, revisar las dos perillas.
- **Secrets**: se inyectan con `--set-secrets` en `cloudbuild.yaml` (ej. `KG_API_KEY`), no en
  el `.env` del front.
- **Modelo y parámetros de LLM**: el front los manda en el payload (`llm_name`,
  `llm_location`, `temperature`, `top_p`, `max_output_tokens`) tomándolos de sus env vars
  `ABCD_*`. Los defaults del backend son los de los campos de `EvaluateRequest`
  (`api_models.py`) y solo aplican si el campo no viene en el request; `set_llm_params()` de
  `configuration.py` aplica tal cual lo que llegó. Resultado: hay dos juegos de defaults, uno
  por repo, y pueden divergir.

## Este repo

- Entrypoint: `server.py` (`uvicorn server:app`). En Docker corre en el puerto `8080`.
- Modelos de request/response: `api_models.py`. Configuración de la corrida:
  `configuration.py`.
- Deploy: `cloudbuild.yaml` (build + push a Artifact Registry + `gcloud run deploy`), con la
  service account `abcd-detector-sa@$PROJECT_ID.iam.gserviceaccount.com`.
- Lint y formato: hay `.pre-commit-config.yaml` y `.pylintrc`. Los hooks corren en el commit y
  el workflow `.github/workflows/ci.yml` los vuelve a correr en push y PR (es el único gate de
  CI). Respetar el estilo existente (indentación de 2 espacios, docstrings) para no pelearse
  con ellos.
- Tests: `tests/`, con pytest.
