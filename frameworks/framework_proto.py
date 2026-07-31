#!/usr/bin/env python3

###########################################################################
#
#    Copyright 2024 Google LLC
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#            https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
###########################################################################

"""Structural interface for an evaluation framework's feature catalog."""

from typing import Protocol
import models


class EvaluationFrameworkProto(Protocol):
  """Structural interface for an evaluation framework's feature catalog."""

  def get_features_by_category_by_group_config(
      self, category: models.AbcdContentFormat
  ) -> dict:
    """Returns feature configs for the given category, grouped by group_by."""
    ...

  def get_feature_by_id(self, feature_id: str) -> models.VideoFeature | None:
    """Looks up a single feature config by id across the whole framework."""
    ...
