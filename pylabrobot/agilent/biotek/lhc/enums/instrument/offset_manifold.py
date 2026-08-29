from __future__ import annotations

import enum


class OffsetManifold(enum.IntEnum):
  """A manifold whose stored X/Y/Z position offsets can be read or written.

  Each fitted manifold carries its own calibrated offsets, because the tubes sit at a different
  place relative to the carrier for every manifold geometry.
  """

  PERI_PUMP = 0
  SYRINGE_8_TUBE = 1
  SYRINGE_16_7_TUBE = 2
  SYRINGE_16_TUBE = 3
  SYRINGE_32_TUBE_LARGE_BORE = 4
  SYRINGE_32_TUBE_SMALL_BORE = 5
  WASHER_128_TUBE = 6
