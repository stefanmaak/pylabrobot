from __future__ import annotations

from typing import Literal

ShakeIntensity = Literal["Variable", "Slow", "Medium", "Fast"]
"""How vigorously the carrier shakes.

The three fixed levels shake at a set frequency; ``"Variable"`` sweeps across the range instead of
holding one frequency.
"""

SHAKE_INTENSITY_TO_BYTE: dict[ShakeIntensity, int] = {
  "Variable": 1,
  "Slow": 2,
  "Medium": 3,
  "Fast": 4,
}
"""The value each intensity is encoded as in a step command."""

SHAKE_INTENSITY_TO_FREQUENCY: dict[ShakeIntensity, float | None] = {
  "Variable": None,
  "Slow": 3.5,
  "Medium": 5.0,
  "Fast": 8.0,
}
"""Shake frequency in Hz per intensity, or None where the frequency is swept."""
