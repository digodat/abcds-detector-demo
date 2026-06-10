# Cloud Run Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exponer el motor de evaluacion ABCD como un endpoint HTTP POST en Google Cloud Run, consumible desde un frontend.

**Architecture:** Se agrega una capa HTTP minima encima de la logica existente: `server.py` es el entry point de FastAPI, `api_models.py` define los modelos Pydantic de request/response, y `main.py` recibe un cambio minimo para retornar resultados. Todo corre en un container Docker con Python 3.11 + ffmpeg. La autenticacion GCP se resuelve via Application Default Credentials del service account asignado al servicio Cloud Run.

**Tech Stack:** FastAPI, uvicorn, Pydantic, Docker (`python:3.11-slim` + ffmpeg), Google Cloud Run, Cloud Secret Manager (para KG API key).

---

## Mapa de archivos

| Accion  | Archivo                  | Responsabilidad                                              |
|---------|--------------------------|--------------------------------------------------------------|
| Crear   | `api_models.py`          | Modelos Pydantic de request/response para el endpoint HTTP   |
| Crear   | `server.py`              | App FastAPI: endpoint `/evaluate` y `/health`                |
| Modificar | `main.py`              | Retornar `list[VideoAssessment]` (cambio backward-compatible) |
| Crear   | `Dockerfile`             | Imagen con Python 3.11 + ffmpeg + dependencias               |
| Crear   | `.dockerignore`          | Excluir notebooks, tests, cache del build context            |

---

## Task 1: Modificar `main.py` para retornar resultados

**Archivos:**
- Modificar: `main.py:36-143`

El cambio es backward-compatible: la funcion actualmente no retorna nada. El CLI no usa el valor de retorno, por lo que agregar un `return` no rompe nada.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_server_integration.py
import pytest
from unittest.mock import MagicMock, patch
from configuration import Configuration
import models


def make_mock_config():
  config = Configuration()
  config.set_parameters(
      project_id="test-project",
      project_zone="us-central1",
      bucket_name="test-bucket",
      knowledge_graph_api_key="",
      bigquery_dataset="ds",
      bigquery_table="",
      assessment_file="",
      extract_brand_metadata=False,
      use_annotations=False,
      use_llms=True,
      run_long_form_abcd=True,
      run_shorts=False,
      features_to_evaluate=[""],
      creative_provider_type="GCS",
      verbose=False,
  )
  config.set_videos(["gs://bucket/video.mp4"])
  config.set_brand_details("TestBrand", "TB", "Product", "Tech", "Buy Now")
  return config


def test_execute_returns_list_of_assessments():
  """execute_abcd_assessment_for_videos should return a list of VideoAssessment."""
  from main import execute_abcd_assessment_for_videos

  config = make_mock_config()

  mock_feature = MagicMock(spec=models.FeatureEvaluation)
  mock_assessment = models.VideoAssessment(
      brand_name="TestBrand",
      video_uri="gs://bucket/video.mp4",
      long_form_abcd_evaluated_features=[mock_feature],
      shorts_evaluated_features=[],
      config=config,
  )

  with patch(
      "main.video_evaluation_service.video_evaluation_service.evaluate_features",
      return_value=[mock_feature],
  ), patch("main.generic_helpers.trim_video"), patch(
      "main.generic_helpers.print_abcd_assessment"
  ), patch(
      "main.generic_helpers.remove_local_video_files"
  ), patch(
      "main.annotations_generation.generate_video_annotations"
  ), patch(
      "main.creative_provider_registry.provider_factory.get_provider"
  ) as mock_provider:
    mock_provider.return_value.get_creative_uris.return_value = [
        "gs://bucket/video.mp4"
    ]
    result = execute_abcd_assessment_for_videos(config)

  assert result is not None
  assert isinstance(result, list)
  assert len(result) == 1
  assert isinstance(result[0], models.VideoAssessment)
  assert result[0].brand_name == "TestBrand"
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

```bash
cd /Users/gastonbaeza/Documents/dev/abcds-detector-demo
python -m pytest tests/test_server_integration.py::test_execute_returns_list_of_assessments -v
```

Resultado esperado: `FAILED` — `assert result is not None` falla porque la funcion retorna `None`.

- [ ] **Step 3: Implementar el cambio en `main.py`**

Reemplazar la funcion `execute_abcd_assessment_for_videos` con esta version que acumula y retorna los assessments:

```python
def execute_abcd_assessment_for_videos(
    config: Configuration,
) -> list[models.VideoAssessment]:
  """Execute ABCD Assessment for all brand videos retrieved by the Creative Provider"""

  creative_provider: creative_provider_proto.CreativeProviderProto = (
      creative_provider_registry.provider_factory.get_provider(
          config.creative_provider_type.value
      )
  )

  video_uris = creative_provider.get_creative_uris(config)
  assessments: list[models.VideoAssessment] = []

  for video_uri in video_uris:

    if (
        config.creative_provider_type == models.CreativeProviderType.GCS
        and "gs://" not in video_uri
    ):
      logging.error(
          "The creative provider GCS does not match with the video uri"
          f" {video_uri}. Stopping execution. Please check."
      )
      break

    if (
        config.creative_provider_type == models.CreativeProviderType.YOUTUBE
        and "https://www.youtube.com" not in video_uri
    ):
      logging.error(
          "The creative provider YOUTUBE does not match with the video uri"
          f" {video_uri}. Stopping execution. Please check."
      )
      break

    print(f"\n\nProcessing ABCD Assessment for video {video_uri}... \n")

    if (
        config.use_annotations
        and config.creative_provider_type == models.CreativeProviderType.GCS
    ):
      annotations_generation.generate_video_annotations(config, video_uri)

    if (
        config.run_long_form_abcd
        and config.creative_provider_type == models.CreativeProviderType.GCS
    ):
      generic_helpers.trim_video(config, video_uri)

    long_form_abcd_evaluated_features: models.FeatureEvaluation = []
    shorts_evaluated_features: models.FeatureEvaluation = []

    if config.run_long_form_abcd:
      long_form_abcd_evaluated_features = (
          video_evaluation_service.video_evaluation_service.evaluate_features(
              config=config,
              video_uri=video_uri,
              features_category=models.VideoFeatureCategory.LONG_FORM_ABCD,
          )
      )

    if config.run_shorts:
      shorts_evaluated_features = (
          video_evaluation_service.video_evaluation_service.evaluate_features(
              config=config,
              video_uri=video_uri,
              features_category=models.VideoFeatureCategory.SHORTS,
          )
      )

    video_assessment: models.VideoAssessment = models.VideoAssessment(
        brand_name=config.brand_name,
        video_uri=video_uri,
        long_form_abcd_evaluated_features=long_form_abcd_evaluated_features,
        shorts_evaluated_features=shorts_evaluated_features,
        config=config,
    )

    if len(long_form_abcd_evaluated_features) > 0:
      generic_helpers.print_abcd_assessment(
          video_assessment.brand_name,
          video_assessment.video_uri,
          long_form_abcd_evaluated_features,
      )
    else:
      logging.info(
          "There are not Full ABCD evaluated features results to display."
      )
    if len(shorts_evaluated_features) > 0:
      generic_helpers.print_abcd_assessment(
          video_assessment.brand_name,
          video_assessment.video_uri,
          shorts_evaluated_features,
      )
    else:
      logging.info(
          "There are not Shorts evaluated features results to display."
      )

    if config.bq_table_name:
      generic_helpers.store_in_bq(config, video_assessment)

    generic_helpers.remove_local_video_files()
    assessments.append(video_assessment)

  return assessments
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

```bash
python -m pytest tests/test_server_integration.py::test_execute_returns_list_of_assessments -v
```

Resultado esperado: `PASSED`.

- [ ] **Step 5: Verificar que los tests existentes siguen pasando**

```bash
python -m pytest tests/ -v
```

Resultado esperado: todos los tests existentes pasan.

---

## Task 2: Crear modelos Pydantic (`api_models.py`)

**Archivos:**
- Crear: `api_models.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar al archivo `tests/test_server_integration.py`:

```python
def test_evaluate_request_defaults():
  """EvaluateRequest should have sane defaults for optional fields."""
  from api_models import EvaluateRequest

  req = EvaluateRequest(
      video_uris=["gs://bucket/video.mp4"],
      bucket_name="my-bucket",
  )

  assert req.use_llms is True
  assert req.run_long_form_abcd is True
  assert req.run_shorts is True
  assert req.use_annotations is False
  assert req.extract_brand_metadata is True
  assert req.creative_provider_type == "GCS"


def test_evaluate_request_requires_video_uris():
  """EvaluateRequest should fail if video_uris is missing."""
  from pydantic import ValidationError
  from api_models import EvaluateRequest

  with pytest.raises(ValidationError):
    EvaluateRequest(bucket_name="my-bucket")


def test_feature_evaluation_response_serialization():
  """FeatureEvaluationResponse should serialize correctly from a FeatureEvaluation."""
  from api_models import FeatureEvaluationResponse
  import models

  mock_feature = MagicMock()
  mock_feature.id = "a_dynamic_start"
  mock_feature.name = "Dynamic Start"
  mock_feature.category = models.VideoFeatureCategory.LONG_FORM_ABCD
  mock_feature.sub_category = models.VideoFeatureSubCategory.ATTRACT
  mock_feature.video_segment = models.VideoSegment.FIRST_5_SECS_VIDEO

  eval_feature = models.FeatureEvaluation(
      feature=mock_feature,
      detected=True,
      confidence_score=0.9,
      rationale="Strong opening",
      evidence="Scene 1",
      strengths="Engaging",
      weaknesses="",
  )

  result = FeatureEvaluationResponse.from_feature_evaluation(eval_feature)

  assert result.feature_id == "a_dynamic_start"
  assert result.detected is True
  assert result.confidence_score == 0.9
  assert result.category == "LONG_FORM_ABCD"
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

```bash
python -m pytest tests/test_server_integration.py::test_evaluate_request_defaults tests/test_server_integration.py::test_evaluate_request_requires_video_uris tests/test_server_integration.py::test_feature_evaluation_response_serialization -v
```

Resultado esperado: `ERROR` — `ModuleNotFoundError: No module named 'api_models'`.

- [ ] **Step 3: Crear `api_models.py`**

```python
"""Pydantic models for the HTTP API layer."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
import models


class EvaluateRequest(BaseModel):
  """Request body for POST /evaluate."""

  # Required
  video_uris: list[str]
  bucket_name: str

  # GCP config — can also come from env vars in server.py
  project_id: Optional[str] = None
  project_zone: Optional[str] = "us-central1"
  knowledge_graph_api_key: Optional[str] = ""

  # Brand
  brand_name: Optional[str] = None
  brand_variations: Optional[str] = ""
  branded_products: Optional[str] = ""
  branded_products_categories: Optional[str] = ""
  branded_call_to_actions: Optional[str] = ""

  # BigQuery output
  bigquery_dataset: Optional[str] = "abcd_detector_ds"
  bigquery_table: Optional[str] = ""

  # Feature flags
  extract_brand_metadata: Optional[bool] = True
  use_annotations: Optional[bool] = False
  use_llms: Optional[bool] = True
  run_long_form_abcd: Optional[bool] = True
  run_shorts: Optional[bool] = True
  creative_provider_type: Optional[str] = "GCS"
  features_to_evaluate: Optional[str] = ""

  # LLM params
  llm_name: Optional[str] = "gemini-2.5-pro"
  llm_location: Optional[str] = "us-central1"
  max_output_tokens: Optional[int] = 65535
  temperature: Optional[float] = 1.0
  top_p: Optional[float] = 0.95


class FeatureEvaluationResponse(BaseModel):
  """Serialized result for a single feature evaluation."""

  feature_id: str
  feature_name: str
  category: str
  sub_category: str
  video_segment: str
  detected: bool
  confidence_score: float
  rationale: str
  evidence: str
  strengths: str
  weaknesses: str

  @classmethod
  def from_feature_evaluation(
      cls, fe: models.FeatureEvaluation
  ) -> FeatureEvaluationResponse:
    """Build response from a FeatureEvaluation dataclass."""
    category = (
        fe.feature.category.value
        if hasattr(fe.feature.category, "value")
        else fe.feature.category
    )
    sub_category = (
        fe.feature.sub_category.value
        if hasattr(fe.feature.sub_category, "value")
        else fe.feature.sub_category
    )
    video_segment = (
        fe.feature.video_segment.value
        if hasattr(fe.feature.video_segment, "value")
        else fe.feature.video_segment
    )
    return cls(
        feature_id=fe.feature.id,
        feature_name=fe.feature.name,
        category=category,
        sub_category=sub_category,
        video_segment=video_segment,
        detected=fe.detected,
        confidence_score=fe.confidence_score,
        rationale=fe.rationale,
        evidence=fe.evidence,
        strengths=fe.strengths,
        weaknesses=fe.weaknesses,
    )


class VideoAssessmentResponse(BaseModel):
  """Serialized result for a single video assessment."""

  brand_name: str
  video_uri: str
  long_form_abcd: list[FeatureEvaluationResponse]
  shorts: list[FeatureEvaluationResponse]

  @classmethod
  def from_video_assessment(
      cls, assessment: models.VideoAssessment
  ) -> VideoAssessmentResponse:
    """Build response from a VideoAssessment dataclass."""
    return cls(
        brand_name=assessment.brand_name,
        video_uri=assessment.video_uri,
        long_form_abcd=[
            FeatureEvaluationResponse.from_feature_evaluation(f)
            for f in assessment.long_form_abcd_evaluated_features
        ],
        shorts=[
            FeatureEvaluationResponse.from_feature_evaluation(f)
            for f in assessment.shorts_evaluated_features
        ],
    )


class EvaluateResponse(BaseModel):
  """Response body for POST /evaluate."""

  status: str
  assessments: list[VideoAssessmentResponse]
```

- [ ] **Step 4: Instalar Pydantic y FastAPI (si no estan)**

```bash
pip install fastapi uvicorn[standard] pydantic
```

Verificar que Pydantic esta disponible:
```bash
python -c "import pydantic; print(pydantic.__version__)"
```

Resultado esperado: version `2.x.x`.

- [ ] **Step 5: Ejecutar los tests para verificar que pasan**

```bash
python -m pytest tests/test_server_integration.py::test_evaluate_request_defaults tests/test_server_integration.py::test_evaluate_request_requires_video_uris tests/test_server_integration.py::test_feature_evaluation_response_serialization -v
```

Resultado esperado: los 3 tests `PASSED`.

---

## Task 3: Crear el servidor FastAPI (`server.py`)

**Archivos:**
- Crear: `server.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_server_integration.py`:

```python
def test_health_endpoint():
  """GET /health should return 200 with status ok."""
  from fastapi.testclient import TestClient
  from server import app

  client = TestClient(app)
  response = client.get("/health")

  assert response.status_code == 200
  assert response.json() == {"status": "ok"}


def test_evaluate_endpoint_calls_execute(monkeypatch):
  """POST /evaluate should call execute_abcd_assessment_for_videos and return results."""
  from fastapi.testclient import TestClient
  from server import app
  import models

  mock_feature = MagicMock()
  mock_feature.id = "a_dynamic_start"
  mock_feature.name = "Dynamic Start"
  mock_feature.category = models.VideoFeatureCategory.LONG_FORM_ABCD
  mock_feature.sub_category = models.VideoFeatureSubCategory.ATTRACT
  mock_feature.video_segment = models.VideoSegment.FIRST_5_SECS_VIDEO

  mock_eval = models.FeatureEvaluation(
      feature=mock_feature,
      detected=True,
      confidence_score=0.85,
      rationale="Good start",
      evidence="Frame 1",
      strengths="Strong",
      weaknesses="",
  )
  mock_config = MagicMock()
  mock_assessment = models.VideoAssessment(
      brand_name="TestBrand",
      video_uri="gs://bucket/video.mp4",
      long_form_abcd_evaluated_features=[mock_eval],
      shorts_evaluated_features=[],
      config=mock_config,
  )

  monkeypatch.setattr(
      "server.execute_abcd_assessment_for_videos",
      lambda config: [mock_assessment],
  )

  client = TestClient(app)
  response = client.post(
      "/evaluate",
      json={
          "video_uris": ["gs://bucket/video.mp4"],
          "bucket_name": "my-bucket",
          "project_id": "my-project",
      },
  )

  assert response.status_code == 200
  data = response.json()
  assert data["status"] == "success"
  assert len(data["assessments"]) == 1
  assert data["assessments"][0]["brand_name"] == "TestBrand"
  assert data["assessments"][0]["long_form_abcd"][0]["feature_id"] == "a_dynamic_start"
  assert data["assessments"][0]["long_form_abcd"][0]["detected"] is True
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

```bash
python -m pytest tests/test_server_integration.py::test_health_endpoint tests/test_server_integration.py::test_evaluate_endpoint_calls_execute -v
```

Resultado esperado: `ERROR` — `ModuleNotFoundError: No module named 'server'`.

- [ ] **Step 3: Crear `server.py`**

```python
"""FastAPI server exposing the ABCD Detector as an HTTP endpoint."""

import logging
import os
from fastapi import FastAPI, HTTPException
from configuration import Configuration
from main import execute_abcd_assessment_for_videos
from api_models import EvaluateRequest, EvaluateResponse, VideoAssessmentResponse

app = FastAPI(title="ABCD Detector API")

logging.basicConfig(level=logging.INFO)


@app.get("/health")
def health():
  """Health check endpoint for Cloud Run."""
  return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest):
  """Evaluate ABCD features for the given video URIs."""

  # project_id can come from the request or from the env var PROJECT_ID
  project_id = request.project_id or os.environ.get("PROJECT_ID", "")
  if not project_id:
    raise HTTPException(
        status_code=400,
        detail="project_id is required. Set it in the request or in the PROJECT_ID env var.",
    )

  # KG API key can come from the request or from the env var KG_API_KEY
  kg_api_key = request.knowledge_graph_api_key or os.environ.get("KG_API_KEY", "")

  config = Configuration()
  config.set_parameters(
      project_id=project_id,
      project_zone=request.project_zone,
      bucket_name=request.bucket_name,
      knowledge_graph_api_key=kg_api_key,
      bigquery_dataset=request.bigquery_dataset,
      bigquery_table=request.bigquery_table,
      assessment_file="",
      extract_brand_metadata=request.extract_brand_metadata,
      use_annotations=request.use_annotations,
      use_llms=request.use_llms,
      run_long_form_abcd=request.run_long_form_abcd,
      run_shorts=request.run_shorts,
      features_to_evaluate=request.features_to_evaluate,
      creative_provider_type=request.creative_provider_type,
      verbose=False,
  )
  config.set_videos(request.video_uris)
  config.set_brand_details(
      brand_name=request.brand_name or "",
      brand_variations=request.brand_variations,
      products=request.branded_products,
      products_categories=request.branded_products_categories,
      call_to_actions=request.branded_call_to_actions,
  )
  config.set_llm_params(
      llm_name=request.llm_name,
      location=request.llm_location,
      max_output_tokens=request.max_output_tokens,
      temperature=request.temperature,
      top_p=request.top_p,
  )

  try:
    assessments = execute_abcd_assessment_for_videos(config)
  except Exception as ex:
    logging.error("Error during ABCD evaluation: %s", ex)
    raise HTTPException(status_code=500, detail=str(ex))

  return EvaluateResponse(
      status="success",
      assessments=[
          VideoAssessmentResponse.from_video_assessment(a) for a in assessments
      ],
  )
```

- [ ] **Step 4: Ejecutar los tests para verificar que pasan**

```bash
python -m pytest tests/test_server_integration.py::test_health_endpoint tests/test_server_integration.py::test_evaluate_endpoint_calls_execute -v
```

Resultado esperado: `PASSED`.

- [ ] **Step 5: Ejecutar todos los tests**

```bash
python -m pytest tests/ -v
```

Resultado esperado: todos pasan.

---

## Task 4: Crear el `Dockerfile`

**Archivos:**
- Crear: `Dockerfile`

No hay test unitario para esto, la verificacion es el build y el run local.

- [ ] **Step 1: Crear `Dockerfile`**

```dockerfile
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
```

> **Por que `sh -c`:** Cloud Run inyecta `$PORT` como variable de entorno. El `sh -c` permite que el shell expanda la variable antes de pasarsela a uvicorn.

- [ ] **Step 2: Crear `.dockerignore`**

```
.git
.pytest_cache
__pycache__
*.pyc
*.pyo
*.ipynb
.pre-commit-config.yaml
.pylintrc
pyproject.toml
docs/
tests/
reduced/
*.egg-info
.venv
venv
```

- [ ] **Step 3: Build local para verificar que no hay errores**

```bash
cd /Users/gastonbaeza/Documents/dev/abcds-detector-demo
docker build -t abcd-detector:local .
```

Resultado esperado: `Successfully built <image-id>` sin errores.

- [ ] **Step 4: Verificar que el server arranca en el container**

```bash
docker run --rm -p 8080:8080 \
  -e PROJECT_ID=test \
  abcd-detector:local
```

En otra terminal:

```bash
curl http://localhost:8080/health
```

Resultado esperado: `{"status":"ok"}`.

Detener el container con `Ctrl+C`.

---

## Task 5: Deploy a Cloud Run

**Pre-requisitos:**
- `gcloud` CLI instalado y autenticado: `gcloud auth login`
- Proyecto GCP configurado: `gcloud config set project <PROJECT_ID>`
- APIs habilitadas (ejecutar una sola vez):

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  videointelligence.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com
```

- [ ] **Step 1: Crear el repositorio en Artifact Registry**

```bash
gcloud artifacts repositories create abcd-detector \
  --repository-format=docker \
  --location=us-central1 \
  --description="ABCD Detector container images"
```

Resultado esperado: `Created repository [abcd-detector]`.

- [ ] **Step 2: Build y push de la imagen**

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud builds submit \
  --tag us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest \
  .
```

Resultado esperado: `SUCCESS` al final del output del build.

> **Alternativa sin Cloud Build (build local):**
> ```bash
> docker build -t us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest .
> gcloud auth configure-docker us-central1-docker.pkg.dev
> docker push us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest
> ```

- [ ] **Step 3: Guardar el KG API Key en Secret Manager**

```bash
echo -n "TU_KG_API_KEY" | gcloud secrets create KG_API_KEY \
  --data-file=- \
  --replication-policy=automatic
```

Resultado esperado: `Created version [1] of the secret [KG_API_KEY]`.

- [ ] **Step 4: Crear el service account para Cloud Run**

```bash
gcloud iam service-accounts create abcd-detector-sa \
  --display-name="ABCD Detector Service Account"
```

Asignar roles necesarios:

```bash
PROJECT_ID=$(gcloud config get-value project)
SA="abcd-detector-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Vertex AI (para Gemini)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user"

# GCS (para leer videos)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA}" \
  --role="roles/storage.objectViewer"

# BigQuery (para escribir resultados)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA}" \
  --role="roles/bigquery.dataEditor"

# Video Intelligence
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA}" \
  --role="roles/cloudvideointelligence.serviceAgent"

# Leer el secret KG_API_KEY
gcloud secrets add-iam-policy-binding KG_API_KEY \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor"
```

Resultado esperado: cada comando imprime `Updated IAM policy`.

- [ ] **Step 5: Deploy a Cloud Run**

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud run deploy abcd-detector \
  --image=us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest \
  --region=us-central1 \
  --service-account=abcd-detector-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
  --set-secrets="KG_API_KEY=KG_API_KEY:latest" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --allow-unauthenticated \
  --port=8080
```

> **Nota sobre `--allow-unauthenticated`:** para un primer deploy de prueba esta bien. Para produccion, quitar este flag y usar autenticacion via Identity Token desde el frontend (ver paso siguiente).

Resultado esperado: output termina con:
```
Service URL: https://abcd-detector-XXXXXXXX-uc.a.run.app
```

- [ ] **Step 6: Verificar el health check del servicio deployado**

```bash
SERVICE_URL=$(gcloud run services describe abcd-detector \
  --region=us-central1 \
  --format="value(status.url)")

curl ${SERVICE_URL}/health
```

Resultado esperado: `{"status":"ok"}`.

- [ ] **Step 7: Test end-to-end con un video real**

```bash
SERVICE_URL=$(gcloud run services describe abcd-detector \
  --region=us-central1 \
  --format="value(status.url)")

curl -X POST ${SERVICE_URL}/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "video_uris": ["gs://TU_BUCKET/TU_VIDEO.mp4"],
    "bucket_name": "TU_BUCKET",
    "use_llms": true,
    "use_annotations": false,
    "run_long_form_abcd": true,
    "run_shorts": false,
    "extract_brand_metadata": true
  }'
```

Resultado esperado: JSON con estructura:
```json
{
  "status": "success",
  "assessments": [
    {
      "brand_name": "...",
      "video_uri": "gs://...",
      "long_form_abcd": [...],
      "shorts": []
    }
  ]
}
```

---

## Notas finales

**URL de la API docs (Swagger):** `${SERVICE_URL}/docs`

**Para llamar el endpoint desde el frontend con autenticacion:**
```javascript
// Obtener Identity Token para Cloud Run
const tokenResponse = await fetch(
  `https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${SA}:generateIdToken`,
  { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ audience: SERVICE_URL }) }
);
const { token } = await tokenResponse.json();

// Llamar al endpoint
const response = await fetch(`${SERVICE_URL}/evaluate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  body: JSON.stringify({ video_uris: [...], bucket_name: '...' })
});
```

**Actualizar el servicio** despues de cambios en el codigo:
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest .
gcloud run deploy abcd-detector --image=us-central1-docker.pkg.dev/${PROJECT_ID}/abcd-detector/abcd-detector:latest --region=us-central1
```
