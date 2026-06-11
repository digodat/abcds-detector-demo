"""Pydantic models for the HTTP API layer."""

from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
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
  features_to_evaluate: Optional[list[str]] = []

  # Output language
  language: Literal["EN", "ES"] = "EN"

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
        if isinstance(fe.feature.category, Enum)
        else str(fe.feature.category)
    )
    sub_category = (
        fe.feature.sub_category.value
        if isinstance(fe.feature.sub_category, Enum)
        else str(fe.feature.sub_category)
    )
    video_segment = (
        fe.feature.video_segment.value
        if isinstance(fe.feature.video_segment, Enum)
        else str(fe.feature.video_segment)
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
  error: Optional[str] = None

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
        error=assessment.error,
    )


class EvaluateResponse(BaseModel):
  """Response body for POST /evaluate."""

  status: str
  assessments: list[VideoAssessmentResponse]
