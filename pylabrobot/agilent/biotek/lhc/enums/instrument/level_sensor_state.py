from __future__ import annotations

import enum


class LevelSensorDataState(enum.IntEnum):
  """Whether a stored level-sensor calibration record holds measured data.

  A record reads back as :attr:`DEFAULT` until a calibration has written measurements into it.
  """

  VALID = 51
  DEFAULT = 119
