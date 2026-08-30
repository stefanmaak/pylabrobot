"""Where in the well a step works."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Positioning:
  """An X, Y and Z offset from the nominal position for the plate in use.

  Values are in the instrument's own motor steps, positive Z being further down into the well.
  What range each axis accepts depends on the step and on the plate, and is checked by validation
  rather than here.

  Attributes:
    z: Depth offset.
    x: Offset across the plate.
    y: Offset along the plate.
  """

  z: int = 0
  x: int = 0
  y: int = 0

  def to_definition(self) -> str:
    """The three fields a protocol file stores, which are ordered Z, X, Y.

    Returns:
      The fields, ``|``-separated.
    """
    return f"{self.z}|{self.x}|{self.y}"

  @classmethod
  def from_definition(cls, z: str, x: str, y: str) -> Positioning:
    """Read the three fields back.

    Widths differ per step, so the range check belongs to the step that owns these fields.

    Args:
      z: The depth field.
      x: The across-plate field.
      y: The along-plate field.

    Returns:
      The offsets.
    """
    return cls(z=int(z), x=int(x), y=int(y))
