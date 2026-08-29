from __future__ import annotations

import enum


class CarrierSpeed(enum.IntEnum):
  """How fast the carrier travels in and out.

  The slow setting reduces splashing when carrying full wells.
  """

  DEFAULT = 0
  SLOW = 1
