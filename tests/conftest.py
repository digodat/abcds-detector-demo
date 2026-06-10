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

"""Pytest configuration: stub out unavailable Google Cloud SDK modules."""

import sys
from unittest.mock import MagicMock

# Stub Google Cloud and Vertex AI SDK modules that are not installed in the
# test environment so that importing project modules does not fail.
_STUB_MODULES = [
    "google.cloud.videointelligence",
    "google.cloud.videointelligence_v1",
    "google.cloud.bigquery",
    "google.cloud.storage",
    "google.cloud.exceptions",
    "google.api_core.exceptions",
    "google.genai",
    "google.genai.types",
    "vertexai",
    "vertexai.preview",
    "vertexai.preview.generative_models",
    "moviepy",
    "moviepy.editor",
]

for _mod in _STUB_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Ensure the google namespace package itself exists so sub-imports resolve.
if "google" not in sys.modules:
    sys.modules["google"] = MagicMock()
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = MagicMock()
