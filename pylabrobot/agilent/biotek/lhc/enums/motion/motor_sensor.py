from __future__ import annotations

import enum


class MotorSensor(enum.IntEnum):
  """Which of a motor's position sensors a fault refers to."""

  NONE = 0
  HOME = 1
  AUX_1 = 2
  AUX_2 = 3
