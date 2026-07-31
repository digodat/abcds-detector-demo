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

"""Factory to register/retrieve evaluation framework implementations."""


class FrameworkFactory:
  """Factory to register/retrieve evaluation framework implementations."""

  def __init__(self):
    self._frameworks = {}

  def register_framework(self, framework_id: str, framework) -> None:
    self._frameworks[framework_id] = framework

  def get_framework(self, framework_id: str):
    framework = self._frameworks.get(framework_id)
    if framework is None:
      raise ValueError(framework_id)
    return framework

  def list_framework_ids(self) -> list[str]:
    return list(self._frameworks.keys())
