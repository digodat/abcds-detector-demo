#!/usr/bin/env python3

###########################################################################
#
#  Copyright 2024 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
###########################################################################

"""Integration tests for server entry point"""

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

  mock_feature = MagicMock(spec=models.VideoFeature)
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


def test_feature_evaluation_response_serialization():
  """FeatureEvaluationResponse should serialize correctly from a FeatureEvaluation."""
  from api_models import FeatureEvaluationResponse
  import models

  mock_feature = MagicMock(spec=models.VideoFeature)
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
  assert result.sub_category == "ATTRACT"
  assert result.video_segment == "FIRST_5_SECS_VIDEO"
