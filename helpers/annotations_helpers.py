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

"""Module to load helper functions to process annotations"""


def calculate_time_seconds(part_obj: dict, part: str) -> float:
  """Calculate time of the provided part of the video
  Args:
      part_obj: part of the video to calculate the time
      part: either start_time_offset or end_time_offset
  Returns:
      time_seconds: the time in seconds
  """
  if part not in part_obj:
    print(f"There is no part time {part} in {part_obj}")
    # TODO (ae) check this later
    return 0
  time_seconds = (
      (part_obj.get(part).get("seconds") or 0)
      + ((part_obj.get(part).get("microseconds") or 0) / 1e6)
      + ((part_obj.get(part).get("nanos") or 0) / 1e9)
  )
  return time_seconds
