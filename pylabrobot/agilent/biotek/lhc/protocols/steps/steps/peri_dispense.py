"""Dispensing through a peristaltic pump."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from pylabrobot.agilent.biotek.lhc.devices.instrument_settings import InstrumentSettings
from pylabrobot.agilent.biotek.lhc.enums.steps.cassette_type import (
  CASSETTE_TYPE_TO_BYTE,
  CassetteType,
)
from pylabrobot.agilent.biotek.lhc.enums.steps.peri_flow_rate import (
  PERI_FLOW_RATE_TO_BYTE,
  PeriFlowRate,
)
from pylabrobot.agilent.biotek.lhc.enums.steps.peri_pump import PERI_PUMP_TO_BYTE, PeriPump
from pylabrobot.agilent.biotek.lhc.enums.steps.step_type import StepType
from pylabrobot.agilent.biotek.lhc.protocols.steps import definition
from pylabrobot.agilent.biotek.lhc.protocols.steps.packing import i8, i16, pad, u8, u16
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_interface import Step
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.groups import (
  PreDispense,
  RandomAccess,
  WellVolumeMap,
)
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.masks import WellMask
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.positioning import Positioning

_PAYLOAD_LENGTH = 23
_RANDOM_ACCESS_PAYLOAD_LENGTH = 66
_DEFINITION_FIELDS = 13

_NO_CASSETTE_REQUIREMENT = 255
_NO_PUMP = 0

_BYTE_TO_CASSETTE_TYPE: dict[int, CassetteType] = {
  value: key for key, value in CASSETTE_TYPE_TO_BYTE.items()
}
_BYTE_TO_PERI_PUMP: dict[int, PeriPump] = {value: key for key, value in PERI_PUMP_TO_BYTE.items()}
_PERI_FLOW_RATES: dict[str, PeriFlowRate] = {"Low": "Low", "Medium": "Medium", "High": "High"}


@dataclass
class PeriDispense(Step):
  """Dispense a volume into every selected well from a peristaltic pump.

  Attributes:
    volume: Volume per tube in µL.
    flow_rate: How fast to dispense.
    cassette_type: The cassette the step requires, or None to accept whatever is fitted.
    positioning: Where in the well to dispense.
    pre_dispense: Whether to pre-dispense first, at what volume and how many times.
    columns: Which columns to dispense into.
    rows: Which rows to dispense into.
    peri_pump: Which pump to drive, or None to leave the choice to the instrument.
    random_access: Whether the step dispenses at random access, and with which head.
    well_volumes: Per-well volumes, sent instead of the selections on a random-access dispense.
  """

  step_type: ClassVar[StepType] = StepType.PERI_DISPENSE

  volume: int = 10
  flow_rate: PeriFlowRate = "High"
  cassette_type: CassetteType | None = "Any"
  positioning: Positioning = field(default_factory=lambda: Positioning(z=336))
  pre_dispense: PreDispense = field(
    default_factory=lambda: PreDispense(enabled=True, volume=10, count=2)
  )
  columns: WellMask = field(default_factory=WellMask.all_columns)
  rows: WellMask = field(default_factory=WellMask.all_rows)
  peri_pump: PeriPump | None = "Primary"
  random_access: RandomAccess = field(default_factory=RandomAccess)
  well_volumes: WellVolumeMap = field(default_factory=WellVolumeMap)

  def to_definition(self, settings: InstrumentSettings) -> str:
    """Write the step as the text a protocol file stores.

    The pre-dispense flow rate is not stored by this step type. The random-access fields are
    written only when the step uses random access and the instrument reads them.

    Args:
      settings: What the instrument has fitted.

    Returns:
      The ``|``-separated definition.
    """
    cassette = (
      _NO_CASSETTE_REQUIREMENT
      if self.cassette_type is None
      else CASSETTE_TYPE_TO_BYTE[self.cassette_type]
    )
    pump = _NO_PUMP if self.peri_pump is None else PERI_PUMP_TO_BYTE[self.peri_pump]
    text = (
      f"{definition.FORMAT_MARKER}|{self.step_type.value}|{self.volume}|{self.flow_rate}"
      f"|{cassette}|{self.positioning.to_definition()}|{self.pre_dispense.enabled}"
      f"|{self.pre_dispense.volume}|{self.pre_dispense.count}"
      f"|{self.columns.to_definition()}|{self.rows.to_definition()}|{pump}"
    )
    if self.random_access.enabled and settings.supports_random_access_tail:
      text += f"|{self.random_access.to_definition()}|{self.well_volumes.to_definition()}"
    return text

  @classmethod
  def from_definition(cls, text: str) -> PeriDispense:
    """Read the step back from its definition text.

    Args:
      text: The ``|``-separated definition.

    Returns:
      The step.

    Raises:
      ValueError: If the definition does not have this step type's layout, or names a flow rate,
        cassette or pump that does not exist.
    """
    own = definition.own_fields_at_least(text, cls.step_type, _DEFINITION_FIELDS)
    (
      volume,
      flow_rate,
      cassette,
      z,
      x,
      y,
      pre_enabled,
      pre_volume,
      pre_count,
      columns,
      rows,
      pump,
    ) = own[:12]
    tail = own[12:]
    if flow_rate not in _PERI_FLOW_RATES:
      raise ValueError(f"unknown peristaltic flow rate: {flow_rate!r}")
    if int(cassette) != _NO_CASSETTE_REQUIREMENT and int(cassette) not in _BYTE_TO_CASSETTE_TYPE:
      raise ValueError(f"unknown cassette type: {cassette!r}")
    if int(pump) != _NO_PUMP and int(pump) not in _BYTE_TO_PERI_PUMP:
      raise ValueError(f"unknown peristaltic pump: {pump!r}")
    return cls(
      volume=definition.number(volume, 16),
      flow_rate=_PERI_FLOW_RATES[flow_rate],
      cassette_type=_BYTE_TO_CASSETTE_TYPE.get(int(cassette)),
      positioning=Positioning(
        z=definition.signed(z, 16), x=definition.signed(x, 16), y=definition.signed(y, 8)
      ),
      pre_dispense=PreDispense(
        enabled=definition.flag(pre_enabled),
        volume=definition.number(pre_volume, 16),
        count=definition.number(pre_count, 8),
      ),
      columns=WellMask.from_definition(columns),
      rows=WellMask.from_definition(rows),
      peri_pump=_BYTE_TO_PERI_PUMP.get(int(pump)),
      random_access=RandomAccess.from_definition(*tail[:2]) if tail else RandomAccess(),
      well_volumes=(WellVolumeMap.from_definition(tail[2]) if len(tail) > 2 else WellVolumeMap()),
    )

  def to_bytes(self, settings: InstrumentSettings) -> bytes:
    """Encode the step as the payload of the command that runs it.

    There are two payloads. A random-access dispense carries the per-well volumes and no
    selections; an ordinary one carries the selections and no volumes, with the row selection
    inverted. With the wider dispense offsets fitted the ordinary payload drops the cassette
    requirement and spends the two bytes on a wider X offset instead.

    An instrument that cannot store the random-access fields never learns the step uses random
    access, so it gets the ordinary payload however the step is configured.

    Args:
      settings: What the instrument has fitted.

    Returns:
      The payload.
    """
    pump = _NO_PUMP if self.peri_pump is None else PERI_PUMP_TO_BYTE[self.peri_pump]
    head = u16(self.volume) + u8(PERI_FLOW_RATE_TO_BYTE[self.flow_rate])
    if self.random_access.enabled and settings.supports_random_access_tail:
      return pad(
        head
        + i16(self.positioning.x)
        + i8(self.positioning.y)
        + i16(self.positioning.z)
        + u16(self.pre_dispense.wire_volume)
        + u8(self.pre_dispense.count)
        + bytes(value for row in self.well_volumes.values for value in row)
        + u8(pump),
        _RANDOM_ACCESS_PAYLOAD_LENGTH,
      )
    if settings.advanced_dispense_offsets:
      offsets = i16(self.positioning.x)
    else:
      cassette = (
        _NO_CASSETTE_REQUIREMENT
        if self.cassette_type is None
        else CASSETTE_TYPE_TO_BYTE[self.cassette_type]
      )
      offsets = u8(cassette) + i8(self.positioning.x)
    return pad(
      head
      + offsets
      + i8(self.positioning.y)
      + i16(self.positioning.z)
      + u16(self.pre_dispense.wire_volume)
      + u8(self.pre_dispense.count)
      + self.columns.to_bytes()
      + self.rows.to_bytes_inverted()
      + u8(pump),
      _PAYLOAD_LENGTH,
    )
