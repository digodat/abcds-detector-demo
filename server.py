"""FastAPI server exposing the ABCD Detector as an HTTP endpoint."""

import logging
import os
from fastapi import FastAPI, HTTPException
from configuration import Configuration
from main import execute_abcd_assessment_for_videos
from api_models import EvaluateRequest, EvaluateResponse, VideoAssessmentResponse
import utils

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
  try:
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

    try:
      assessments = execute_abcd_assessment_for_videos(config)
    except HTTPException:
      raise
    except Exception as ex:
      logging.error("Error during ABCD evaluation: %s", ex)
      raise HTTPException(status_code=500, detail=str(ex))
  finally:
    config.cleanup()

  return EvaluateResponse(
      status="success",
      assessments=[
          VideoAssessmentResponse.from_video_assessment(a) for a in assessments
      ],
  )
