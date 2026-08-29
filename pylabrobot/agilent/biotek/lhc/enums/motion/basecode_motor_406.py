from __future__ import annotations

import enum


class Basecode406Motor(enum.IntEnum):
  """Motor numbering used by EL406 firmware fault codes."""

  CARRIER_X = 0
  CARRIER_Y = 1
  DISPENSE_HEAD_Z = 2
  WASH_HEAD_Z = 3
  SYRINGE_A = 4
  SYRINGE_B = 5
  PERI_PUMP_PRIMARY = 6
