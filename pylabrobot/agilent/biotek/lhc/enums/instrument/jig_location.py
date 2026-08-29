from __future__ import annotations

import enum


class JigLocation(enum.IntEnum):
  """Which of the two carrier positions a calibration jig is placed in."""

  LEFT = 0
  RIGHT = 1
