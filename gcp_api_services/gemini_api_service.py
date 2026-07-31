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

"""Module to load helper functions and classes to interact with Vertex AI"""

import time
import functools
from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from configuration import Configuration
from prompts.prompt_generator import PromptConfig
from models import LLMParameters


DEFAULT_CONFIG = LLMParameters()


@functools.lru_cache(maxsize=8)
def _get_genai_client(project_id: str, location: str) -> genai.Client:
  """Returns a cached GenAI client per (project, location).

  Reusing the client avoids recreating its gRPC connection pool on every call
  and retry. Cached by location because it is configurable per request; the
  small bound keeps the handful of real (project, location) clients alive
  without growing unbounded. The client is thread-safe for generate_content,
  so it is shared across the evaluation thread pool.
  """
  return genai.Client(vertexai=True, project=project_id, location=location)


class GeminiAPIService:
  """Gemini API Service to leverage the Vertex APIs for inference"""

  def __init__(self, project_id: str):
    self.project_id = project_id

  def execute_gemini_with_genai(
      self, prompt_config: PromptConfig, llm_params: LLMParameters | None = None
  ):
    """Executes Gemini using the GenAI library"""
    if not llm_params:
      llm_params = DEFAULT_CONFIG
    # Reuse a cached client across calls/retries instead of recreating it
    client = _get_genai_client(self.project_id, llm_params.location)
    # Build the request once; it does not change across retries.
    contents = self._get_modality_params_genai(prompt_config.prompt, llm_params)
    generate_content_config = types.GenerateContentConfig(
        temperature=llm_params.generation_config.get("temperature"),
        top_p=llm_params.generation_config.get("top_p"),
        seed=0,
        max_output_tokens=llm_params.generation_config.get("max_output_tokens"),
        response_modalities=["TEXT"],  # Just text for now
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
            ),
        ],
        system_instruction=[
            types.Part.from_text(text=prompt_config.system_instructions)
        ],
        response_mime_type="application/json",
        response_schema=llm_params.generation_config.get("response_schema"),
    )
    # Retry call for retriable errors
    retries = 3
    for this_retry in range(retries):
      try:
        # Get response from Gemini
        response = client.models.generate_content(
            model=llm_params.model_name,
            contents=contents,
            config=generate_content_config,
        )

        return response.parsed
      except ResourceExhausted as ex:
        print(f"QUOTA RETRY: {this_retry + 1}. ERROR {str(ex)} ...")
        wait = 10 * 2**this_retry
        time.sleep(wait)
      except AttributeError as ex:
        error_message = str(ex)
        if "Content has no parts" in error_message:
          # Retry request
          print(
              f"Error: {ex} Gemini might be blocking the response due to safety"
              f" issues. Retrying {retries} times using exponential backoff."
              f" Retry number {this_retry + 1}...\n"
          )
          wait = 10 * 2**this_retry
          time.sleep(wait)
      except Exception as ex:
        print("GENERAL EXCEPTION...\n")
        error_message = str(ex)
        # Check quota issues for now
        if (
            "429" in error_message
            or "503 The service is currently unavailable" in error_message
            or "500 Internal error encountered" in error_message
        ):
          print(
              f"Error {error_message}. Retrying {retries} times using"
              f" exponential backoff. Retry number {this_retry + 1}...\n"
          )
          # Retry request
          wait = 10 * 2**this_retry
          time.sleep(wait)
        else:
          print(
              f"ERROR: the following issue can't be retried: {error_message}\n"
          )
          # Raise exception for non-retriable errors
          raise

  def _get_modality_params_genai(
      self, prompt: str, params: LLMParameters
  ) -> list[any]:
    """Build the modality params based on the type of llm capability to use
    Args:
        prompt: a string with the prompt for LLM
        model_params: the model params for inference, see defaults above
    Returns:
        modality_params: list of modality params based on the model capability to use
    """
    if params.modality["type"] == "video":
      mime_type = f"video/{params.modality['video_uri'].rsplit('.', 1)[-1]}"
      video = types.Part.from_uri(
          file_uri=params.modality["video_uri"], mime_type=mime_type
      )
      return [
          types.Content(
              role="user", parts=[video, types.Part.from_text(text=prompt)]
          )
      ]
    elif params.modality["type"] == "text":
      return [
          types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
      ]

    return []


def get_gemini_api_service(config: Configuration) -> GeminiAPIService:
  """Gets Vertex AI service to interact with Gemini"""
  gemini_api_service = GeminiAPIService(config.project_id)

  return gemini_api_service
