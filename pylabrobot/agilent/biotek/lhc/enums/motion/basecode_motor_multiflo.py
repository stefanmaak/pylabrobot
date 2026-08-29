from __future__ import annotations

import enum


class BasecodeMultiFloMotor(enum.IntEnum):
  """Motor numbering used by MultiFlo firmware fault codes."""

  CARRIER_X = 0
  CARRIER_Y = 1
  DISPENSE_HEAD_Z = 2
  PERI_PUMP_SECONDARY = 3
  SYRINGE_A = 4
  SYRINGE_B = 5
  PERI_PUMP_PRIMARY = 6
  STRIP_WASHER_SYRINGE = 7
  ASPIRATE_HEAD_Z = 8
  PERI_RANDOM_ACCESS_Y = 9
