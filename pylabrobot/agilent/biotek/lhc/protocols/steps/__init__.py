"""Protocol steps: what they hold, how a protocol file stores them, how they are encoded."""

from __future__ import annotations

from pylabrobot.agilent.biotek.lhc.enums.steps.step_type import StepType
from pylabrobot.agilent.biotek.lhc.protocols.steps import definition
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_interface import Step


def step_from_definition(text: str) -> Step:
  """Read a step of any type back from its definition text.

  Which type it is comes from the definition itself. A composite step's parts are separated
  before the step type is read, so the type of the whole is what decides.

  Args:
    text: The ``|``-separated definition, or the ``#``-joined parts of a composite one.

  Returns:
    The step, of whichever class implements its type.

  Raises:
    ValueError: If the definition names no known step type, or does not have that type's layout.
  """
  from pylabrobot.agilent.biotek.lhc.protocols.steps.steps import STEP_CLASSES

  found, start = definition.fields(text.split("#")[0])
  step_type = StepType(int(found[start]))
  if step_type not in STEP_CLASSES:
    raise ValueError(f"no step class for {step_type.name}")
  return STEP_CLASSES[step_type].from_definition(text)


__all__ = ["Step", "step_from_definition"]
