"""Reading the delimited text a protocol file stores a step as.

Every step in a protocol file is one ``|``-separated string. The first field is an optional format
marker, the field after it is the step type, and the rest belong to that type. These helpers cover
what all step types share: splitting, locating the step-type field and converting a single field
with the width the format uses for it.
"""

from __future__ import annotations

from pylabrobot.agilent.biotek.lhc.enums.steps.buffer import Buffer
from pylabrobot.agilent.biotek.lhc.enums.steps.step_type import StepType
from pylabrobot.agilent.biotek.lhc.enums.steps.travel_rate import TRAVEL_RATE_TO_BYTE, TravelRate
from pylabrobot.agilent.biotek.lhc.enums.steps.wash_format import (
  WASH_FORMAT_TO_BYTE,
  WashFormat,
)

FORMAT_MARKER = "DV103"
"""The format marker written on every step this package produces."""

_MARKER_PREFIX = "DV"
_MARKER_VERSION = 103.0


def fields(text: str, empty_ok: bool = False) -> tuple[list[str], int]:
  """Split a step definition and say where its step-type field sits.

  Args:
    text: The step definition.
    empty_ok: Whether an empty field holds its place. Some step types write empty fields and count
      them; the rest drop them.

  Returns:
    The fields, and the index of the step-type field among them.

  Raises:
    ValueError: If the definition is empty, or carries a newer format marker than this package
      reads.
  """
  found = text.split("|")
  if not empty_ok:
    found = [field for field in found if field]
  if not found:
    raise ValueError("empty step definition")
  if not found[0].startswith(_MARKER_PREFIX):
    return found, 0
  if float(found[0][len(_MARKER_PREFIX) :]) > _MARKER_VERSION:
    raise ValueError(f"step definition {found[0]} is newer than {FORMAT_MARKER}")
  return found, 1


def own_fields(text: str, step_type: StepType, count: int, empty_ok: bool = False) -> list[str]:
  """The fields belonging to a step type whose layout is a fixed length.

  Args:
    text: The step definition.
    step_type: The step type the layout belongs to, named in the error message.
    count: How many fields the layout has, counting the step-type field.
    empty_ok: Whether an empty field holds its place.

  Returns:
    The fields after the step-type field, ``count - 1`` of them.

  Raises:
    ValueError: If the definition has a different number of fields. A definition one field short
      is another instrument family's, not a repairable one.
  """
  found, start = fields(text, empty_ok)
  if len(found) - start != count:
    raise ValueError(f"{step_type.name} expects {count} fields, got {len(found) - start}: {text!r}")
  return found[start + 1 :]


def own_fields_at_least(
  text: str, step_type: StepType, minimum: int, empty_ok: bool = False
) -> list[str]:
  """The fields belonging to a step type whose layout ends in an optional tail.

  What a surplus means depends on how much of it there is, so the caller decides.

  Args:
    text: The step definition.
    step_type: The step type the layout belongs to, named in the error message.
    minimum: The shortest the layout can be, counting the step-type field.
    empty_ok: Whether an empty field holds its place.

  Returns:
    The fields after the step-type field, at least ``minimum - 1`` of them.

  Raises:
    ValueError: If the definition has fewer fields than that.
  """
  found, start = fields(text, empty_ok)
  if len(found) - start < minimum:
    raise ValueError(
      f"{step_type.name} expects at least {minimum} fields, got {len(found) - start}: {text!r}"
    )
  return found[start + 1 :]


def flag(field: str) -> bool:
  """Read a boolean field.

  Args:
    field: The field text, ``"True"`` or ``"False"`` in any case.

  Returns:
    What it says.

  Raises:
    ValueError: If it says anything else.
  """
  lowered = field.strip().lower()
  if lowered in ("true", "false"):
    return lowered == "true"
  raise ValueError(f"not a boolean: {field!r}")


def number(field: str, bits: int) -> int:
  """Read an unsigned field of a given width.

  Args:
    field: The field text.
    bits: How many bits the value is stored in.

  Returns:
    The value.

  Raises:
    ValueError: If it does not fit, which makes the whole definition unreadable rather than
      merely invalid.
  """
  value = int(field)
  if not 0 <= value < 1 << bits:
    raise ValueError(f"{value} does not fit in {bits} unsigned bits")
  return value


def signed(field: str, bits: int) -> int:
  """Read a signed field of a given width, as the offsets are stored.

  Args:
    field: The field text.
    bits: How many bits the value is stored in.

  Returns:
    The value.

  Raises:
    ValueError: If it does not fit.
  """
  value = int(field)
  if not -(1 << (bits - 1)) <= value < 1 << (bits - 1):
    raise ValueError(f"{value} does not fit in {bits} signed bits")
  return value


BUFFERS: dict[str, Buffer] = {"A": "A", "B": "B", "C": "C", "D": "D"}
"""The buffer inlet each buffer field names."""

TRAVEL_RATES: dict[str, TravelRate] = {rate: rate for rate in TRAVEL_RATE_TO_BYTE}
"""The travel rate each travel-rate field names."""

WASH_FORMATS: dict[str, WashFormat] = {value: value for value in WASH_FORMAT_TO_BYTE}
"""The wash format each format field names."""
