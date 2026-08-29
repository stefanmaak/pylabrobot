from __future__ import annotations

from typing import Literal

FillPattern = Literal["Column", "Row"]
"""The order in which a random-access dispense visits the selected wells.

A step that does not choose an order carries None.
"""

FILL_PATTERN_TO_BYTE: dict[FillPattern, int] = {"Column": 0, "Row": 1}
"""The value each pattern is encoded as in a step command. No pattern encodes 255."""
