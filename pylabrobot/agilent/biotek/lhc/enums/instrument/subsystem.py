from __future__ import annotations

import enum


class Subsystem(enum.IntEnum):
  """A liquid-moving subsystem, addressed by calibration and verification routines.

  The verify-jig members are not pumps but the measurement fixtures used to calibrate the
  dispense, aspirate and single-well positions.
  """

  PERI_PUMP_PRIMARY = 0
  SYRINGE_A = 1
  SYRINGE_B = 2
  WASHER = 3
  PERI_PUMP_SECONDARY = 4
  DISPENSER_VERIFY_JIG = 5
  STRIP_WASHER_ASPIRATE = 6
  STRIP_WASHER_DISPENSE = 7
  ASPIRATE_VERIFY_JIG = 8
  SINGLE_WELL_VERIFY_JIG = 9
