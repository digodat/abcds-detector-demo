"""FastAPI server exposing the ABCD Detector as an HTTP endpoint."""

import asyncio
import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from configuration import Configuration
from main import execute_abcd_assessment_for_videos
from api_models import EvaluateRequest, EvaluateResponse, VideoAssessmentResponse
import utils

app = FastAPI(title="ABCD Detector API")

logging.basicConfig(level=logging.INFO)


def _resolve_project_id() -> str:
  """Resolve GCP project ID: ADC first, then PROJECT_ID env var."""
  try:
    import google.auth
    _, project = google.auth.default()
    if project:
      return project
  except Exception:
    pass
  return os.environ.get("PROJECT_ID", "")


def _setup_config(
    config: Configuration,
    request: EvaluateRequest,
    project_id: str,
    kg_api_key: str,
) -> None:
  """Populate config from the request. Raises HTTPException on invalid input."""
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
      language=request.language,
      audio_language_code=request.audio_language_code,
  )
  config.set_videos(request.video_uris)
  config.set_brand_details(
      brand_name=request.brand_name or "",
      brand_variations=request.brand_variations,
      products=request.branded_products,
      products_categories=request.branded_products_categories,
      call_to_actions=request.branded_call_to_actions,
  )

  if utils.invalid_brand_metadata(config):
    raise HTTPException(
        status_code=400,
        detail=(
            "extract_brand_metadata is disabled but no brand details were"
            " provided. Enable it or supply brand_name, brand_variations,"
            " branded_products, and branded_products_categories."
        ),
    )

  config.set_llm_params(
      llm_name=request.llm_name,
      location=request.llm_location,
      max_output_tokens=request.max_output_tokens,
      temperature=request.temperature,
      top_p=request.top_p,
  )


@app.get("/health")
def health():
  """Health check endpoint for Cloud Run."""
  return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest):
  """Evaluate ABCD features for the given video URIs."""

  project_id = request.project_id or _resolve_project_id()
  if not project_id:
    raise HTTPException(
        status_code=400,
        detail="project_id could not be determined. Pass it in the request body or ensure the service runs with a GCP service account.",
    )

  kg_api_key = request.knowledge_graph_api_key or os.environ.get("KG_API_KEY", "")

  config = Configuration()
  try:
    _setup_config(config, request, project_id, kg_api_key)

    try:
      assessments = execute_abcd_assessment_for_videos(config)
    except HTTPException:
      raise
    except Exception as ex:
      logging.error("Error during ABCD evaluation: %s", ex)
      raise HTTPException(status_code=500, detail=str(ex))
  finally:
    config.cleanup()

  assessment_responses = [
      VideoAssessmentResponse.from_video_assessment(a) for a in assessments
  ]
  status = "partial" if any(a.error for a in assessment_responses) else "success"
  return EvaluateResponse(status=status, assessments=assessment_responses)


@app.post("/evaluate/stream")
async def evaluate_stream(request: EvaluateRequest):
  """Evaluate ABCD features and stream progress as Server-Sent Events (text/event-stream)."""

  project_id = request.project_id or _resolve_project_id()
  if not project_id:
    raise HTTPException(
        status_code=400,
        detail="project_id could not be determined. Pass it in the request body or ensure the service runs with a GCP service account.",
    )

  kg_api_key = request.knowledge_graph_api_key or os.environ.get("KG_API_KEY", "")
  loop = asyncio.get_running_loop()
  event_queue: asyncio.Queue = asyncio.Queue()

  config = Configuration()

  # Bridge sync evaluation thread to async SSE generator via asyncio queue
  def emit(event: dict) -> None:
    loop.call_soon_threadsafe(event_queue.put_nowait, event)

  config.progress_callback = emit

  try:
    _setup_config(config, request, project_id, kg_api_key)
  except HTTPException:
    config.cleanup()
    raise

  def run_in_thread() -> None:
    try:
      assessments = execute_abcd_assessment_for_videos(config)
      assessment_responses = [
          VideoAssessmentResponse.from_video_assessment(a) for a in assessments
      ]
      stream_status = "partial" if any(a.error for a in assessment_responses) else "success"
      loop.call_soon_threadsafe(
          event_queue.put_nowait,
          {
              "type": "done",
              "status": stream_status,
              "assessments": [a.model_dump(mode="json") for a in assessment_responses],
          },
      )
    except Exception as ex:
      logging.error("Error during streaming ABCD evaluation: %s", ex)
      loop.call_soon_threadsafe(
          event_queue.put_nowait,
          {"type": "error", "detail": str(ex)},
      )
    finally:
      config.cleanup()
      loop.call_soon_threadsafe(event_queue.put_nowait, None)

  executor_future = loop.run_in_executor(None, run_in_thread)

  async def event_generator():
    try:
      while True:
        try:
          event = await asyncio.wait_for(event_queue.get(), timeout=25.0)
        except asyncio.TimeoutError:
          yield ": keepalive\n\n"
          continue

        if event is None:
          break
        yield f"data: {json.dumps(event)}\n\n"
        if event.get("type") in ("done", "error"):
          break
    finally:
      await executor_future

  return StreamingResponse(
      event_generator(),
      media_type="text/event-stream",
      headers={
          "Cache-Control": "no-cache",
          "X-Accel-Buffering": "no",
      },
  )
