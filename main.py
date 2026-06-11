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

"""Module to execute the ABCD Detector Assessment"""

import time
import traceback
import logging
import models
import utils
from annotations_evaluation import annotations_generation
from helpers import generic_helpers
from configuration import Configuration
from creative_providers import creative_provider_proto
from creative_providers import creative_provider_registry
from evaluation_services import video_evaluation_service


def _emit(config: Configuration, event: dict) -> None:
  if config.progress_callback:
    config.progress_callback(event)


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

  for idx, video_uri in enumerate(video_uris):

    _emit(config, {"type": "video_start", "video_uri": video_uri, "index": idx + 1, "total": len(video_uris)})

    try:
      # Validate that creative provider matches the video URI format
      if (
          config.creative_provider_type == models.CreativeProviderType.GCS
          and "gs://" not in video_uri
      ):
        raise ValueError(
            f"Provider type GCS does not match video URI '{video_uri}'."
            " Use a gs:// URI or set creative_provider_type to 'YOUTUBE'."
        )

      if (
          config.creative_provider_type == models.CreativeProviderType.YOUTUBE
          and "https://www.youtube.com" not in video_uri
      ):
        raise ValueError(
            f"Provider type YOUTUBE does not match video URI '{video_uri}'."
            " Use a YouTube URL or set creative_provider_type to 'GCS'."
        )

      print(f"\n\nProcessing ABCD Assessment for video {video_uri}... \n")

      # Generate video annotations for custom features. Annotations are supported only for GCS providers
      if (
          config.use_annotations
          and config.creative_provider_type == models.CreativeProviderType.GCS
      ):
        _emit(config, {"type": "step", "step": "annotations", "status": "running", "video_uri": video_uri})
        annotations_generation.generate_video_annotations(config, video_uri)
        _emit(config, {"type": "step", "step": "annotations", "status": "done", "video_uri": video_uri})

      # Full ABCD features require 1st_5_secs videos only for GCS providers
      if (
          config.run_long_form_abcd
          and config.creative_provider_type == models.CreativeProviderType.GCS
      ):
        _emit(config, {"type": "step", "step": "trim", "status": "running", "video_uri": video_uri})
        generic_helpers.trim_video(config, video_uri)
        _emit(config, {"type": "step", "step": "trim", "status": "done", "video_uri": video_uri})

      # Execute ABCD Assessment
      long_form_abcd_evaluated_features: models.FeatureEvaluation = []
      shorts_evaluated_features: models.FeatureEvaluation = []

      if config.run_long_form_abcd:
        _emit(config, {"type": "step", "step": "long_form_abcd", "status": "running", "video_uri": video_uri})
        long_form_abcd_evaluated_features = (
            video_evaluation_service.video_evaluation_service.evaluate_features(
                config=config,
                video_uri=video_uri,
                features_category=models.VideoFeatureCategory.LONG_FORM_ABCD,
            )
        )
        _emit(config, {"type": "step", "step": "long_form_abcd", "status": "done", "video_uri": video_uri})

      if config.run_shorts:
        _emit(config, {"type": "step", "step": "shorts", "status": "running", "video_uri": video_uri})
        shorts_evaluated_features = (
            video_evaluation_service.video_evaluation_service.evaluate_features(
                config=config,
                video_uri=video_uri,
                features_category=models.VideoFeatureCategory.SHORTS,
            )
        )
        _emit(config, {"type": "step", "step": "shorts", "status": "done", "video_uri": video_uri})

      video_assessment: models.VideoAssessment = models.VideoAssessment(
          brand_name=config.brand_name,
          video_uri=video_uri,
          long_form_abcd_evaluated_features=long_form_abcd_evaluated_features,
          shorts_evaluated_features=shorts_evaluated_features,
          config=config,
      )

      assessments.append(video_assessment)

      # Print assessments for Full ABCD and Shorts and store results
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
        _emit(config, {"type": "step", "step": "bigquery", "status": "running", "video_uri": video_uri})
        generic_helpers.store_in_bq(config, video_assessment)
        _emit(config, {"type": "step", "step": "bigquery", "status": "done", "video_uri": video_uri})

      # Remove local version of video files
      generic_helpers.remove_local_video_files(config)

      _emit(config, {"type": "video_done", "video_uri": video_uri, "index": idx + 1, "total": len(video_uris)})

    except Exception as ex:
      logging.error("Error processing video %s: %s", video_uri, ex)
      generic_helpers.remove_local_video_files(config)
      assessments.append(models.VideoAssessment(
          brand_name=config.brand_name,
          video_uri=video_uri,
          long_form_abcd_evaluated_features=[],
          shorts_evaluated_features=[],
          config=config,
          error=str(ex),
      ))
      _emit(config, {"type": "video_error", "video_uri": video_uri, "index": idx + 1, "total": len(video_uris), "detail": str(ex)})

  config.cleanup()
  return assessments


def main(arg_list: list[str] | None = None) -> None:
  """Main ABCD Assessment execution. See docstring and args.

  Args:
    arg_list: A list of command line arguments

  """

  try:
    args = utils.parse_args(arg_list)

    config = utils.build_abcd_params_config(args)

    if utils.invalid_brand_metadata(config):
      logging.error(
          "The Extract Brand Metadata option is disabled and no brand details"
          " were defined. \n"
      )
      logging.error("Please enable the option or define brand details. \n")
      return

    start_time = time.time()
    logging.info("Starting ABCD assessment... \n")

    if config.video_uris:
      try:
        execute_abcd_assessment_for_videos(config)
        logging.info("Finished ABCD assessment. \n")
      finally:
        config.cleanup()
    else:
      logging.info("There are no videos to process. \n")

    logging.info(
        "ABCD assessment took - %s mins. - \n", (time.time() - start_time) / 60
    )
  except Exception as ex:
    logging.error("ERROR: %s", ex)
    traceback.print_exc()


if __name__ == "__main__":
  main()
