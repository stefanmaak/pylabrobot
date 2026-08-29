from __future__ import annotations

import enum


class Basecode405TSMotor(enum.IntEnum):
  """Motor numbering used by 405 TS firmware fault codes."""

  CARRIER_X = 0
  CARRIER_Y = 1
  WASH_HEAD_Z = 2
  LEVEL_SENSE_Y = 3
