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

"""Module that registers all evaluation frameworks."""

from features_repository import feature_configs_handler
from frameworks import framework_factory

framework_factory_instance = framework_factory.FrameworkFactory()


def register_frameworks():
  """Register the different evaluation frameworks."""
  framework_factory_instance.register_framework(
      "abcd", feature_configs_handler.features_configs_handler
  )


register_frameworks()
