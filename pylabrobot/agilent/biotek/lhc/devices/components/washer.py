"""Washing a plate.

The capability object an instrument with a wash manifold, a strip washer manifold, or both exposes.
Every method here is one step run on its own: it builds the step, runs the check that decides
whether the instrument can run it, brackets it in a batch if one is not open already, and waits for
it to finish. Doing several of them inside ``async with device.batch():`` pays the opening cost once.

The arguments spelled out are the ones a caller usually sets. Everything a step groups -- where in
the well to work, whether to pre-dispense, what to do between cycles -- is passed as the group it
belongs to, and left out to keep the step's own default. A step needing more than that is built
outright and handed to ``device.run_step()``.
"""

from __future__ import annotations

from pylabrobot.agilent.biotek.lhc.devices.execution import run_steps
from pylabrobot.agilent.biotek.lhc.devices.runtime import Runtime
from pylabrobot.agilent.biotek.lhc.enums.steps.buffer import Buffer
from pylabrobot.agilent.biotek.lhc.enums.steps.travel_rate import TravelRate
from pylabrobot.agilent.biotek.lhc.enums.steps.wash_format import WashFormat
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.groups import (
  PreDispense,
  SecondaryAspirate,
  Sectors,
  Submerge,
  VacuumDelay,
  WashStages,
)
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.masks import WellMask
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.positioning import Positioning
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_aspirate import ManifoldAspirate
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_auto_clean import (
  ManifoldAutoClean,
)
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_dispense import ManifoldDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_prime import ManifoldPrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_wash import ManifoldWash
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.shake_soak import ShakeSoak
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_aspirate import StripAspirate
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_dispense import StripDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_prime import StripPrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_wash import StripWash
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.syringe_dispense import SyringeDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.wash_1536 import Wash1536


class PlateWasher:
  """The wash manifolds an instrument is fitted with.

  Args:
    runtime: The state of the device this belongs to, which is where the link, the fitted options
      and the plate on the carrier come from.
  """

  def __init__(self, runtime: Runtime) -> None:
    self._runtime = runtime

  async def wash(
    self,
    cycles: int = 3,
    wash_format: WashFormat = "Plate",
    dispense: ManifoldDispense | None = None,
    aspirate: ManifoldAspirate | None = None,
    stages: WashStages | None = None,
    shake_soak: ShakeSoak | None = None,
    bottom_wash: ManifoldDispense | None = None,
    final_aspirate: ManifoldAspirate | None = None,
    sectors: Sectors | None = None,
  ) -> None:
    """Wash the plate through the wash manifold.

    Args:
      cycles: How many wash cycles to run.
      wash_format: Whether to wash the whole plate, selected sectors or selected strips.
      dispense: The dispense that refills the well each cycle.
      aspirate: The aspirate that empties the well at the start of each cycle.
      stages: Which optional stages run.
      shake_soak: The pause after each dispense.
      bottom_wash: The dispense that washes the bottom of the well, when that stage runs.
      final_aspirate: The aspirate that empties the well after the last cycle.
      sectors: Which sectors to wash, when the format selects sectors.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = ManifoldWash(cycles=cycles, wash_format=wash_format)
    if dispense is not None:
      step.dispense = dispense
    if aspirate is not None:
      step.aspirate = aspirate
    if stages is not None:
      step.stages = stages
    if shake_soak is not None:
      step.shake_soak = shake_soak
    if bottom_wash is not None:
      step.bottom_wash = bottom_wash
    if final_aspirate is not None:
      step.final_aspirate = final_aspirate
    if sectors is not None:
      step.sectors = sectors
    await run_steps(self._runtime, [step])

  async def aspirate(
    self,
    travel_rate: TravelRate = "3",
    delay: int = 0,
    vacuum_filtration: bool = False,
    positioning: Positioning | None = None,
    secondary: SecondaryAspirate | None = None,
    columns: WellMask | None = None,
  ) -> None:
    """Draw the wells empty through the wash manifold.

    Args:
      travel_rate: How fast the tips descend into the well.
      delay: How long to keep aspirating once the tips are down, in ms. Under vacuum filtration
        this is the filtration time in seconds instead.
      vacuum_filtration: Whether to pull the wells through a filter plate instead of aspirating
        from above. Not available on a 1536-well plate.
      positioning: Where in the well to aspirate.
      secondary: Whether to aspirate a second time, in what pattern and where.
      columns: Which columns to aspirate.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = ManifoldAspirate(
      travel_rate=travel_rate, delay=delay, vacuum_filtration=vacuum_filtration
    )
    if positioning is not None:
      step.positioning = positioning
    if secondary is not None:
      step.secondary = secondary
    if columns is not None:
      step.columns = columns
    await run_steps(self._runtime, [step])

  async def dispense(
    self,
    volume: int,
    buffer: Buffer = "A",
    flow_rate: int = 7,
    positioning: Positioning | None = None,
    pre_dispense: PreDispense | None = None,
    vacuum: VacuumDelay | None = None,
  ) -> None:
    """Dispense into every selected well through the wash manifold.

    Args:
      volume: Volume per well in µL.
      buffer: Which buffer inlet to draw from.
      flow_rate: How fast to dispense. The two slowest rates need the cell washing module and a
        96-tube dual-action manifold.
      positioning: Where in the well to dispense.
      pre_dispense: Whether to pre-dispense first, and at what volume and rate.
      vacuum: Whether to hold the vacuum off until a volume has been dispensed.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = ManifoldDispense(volume=volume, buffer=buffer, flow_rate=flow_rate)
    if positioning is not None:
      step.positioning = positioning
    if pre_dispense is not None:
      step.pre_dispense = pre_dispense
    if vacuum is not None:
      step.vacuum = vacuum
    await run_steps(self._runtime, [step])

  async def prime(
    self,
    volume: int = 40_000,
    buffer: Buffer = "A",
    flow_rate: int = 9,
    prime_low_flow_path: bool = True,
    low_flow_path_volume: int = 5_000,
    submerge: Submerge | None = None,
  ) -> None:
    """Pump fluid through the wash manifold until the lines are full.

    Args:
      volume: Volume to pump in µL. The instrument runs this at millilitre resolution.
      buffer: Which buffer inlet to draw from.
      flow_rate: How fast to pump.
      prime_low_flow_path: Whether to prime the low flow path as well.
      low_flow_path_volume: Volume to pump through the low flow path in µL, when it is primed.
      submerge: Whether to leave the tips in fluid afterwards, and for how long.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = ManifoldPrime(
      volume=volume,
      buffer=buffer,
      flow_rate=flow_rate,
      prime_low_flow_path=prime_low_flow_path,
      low_flow_path_volume=low_flow_path_volume,
    )
    if submerge is not None:
      step.submerge = submerge
    await run_steps(self._runtime, [step])

  async def auto_clean(self, duration: int = 3600, buffer: Buffer = "A") -> None:
    """Soak the wash manifold in cleaning fluid.

    Args:
      duration: How long to clean, in seconds. The instrument runs this at whole-minute resolution.
      buffer: Which buffer inlet the cleaning fluid comes from.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    await run_steps(self._runtime, [ManifoldAutoClean(duration=duration, buffer=buffer)])

  async def wash_1536(
    self,
    cycles: int = 3,
    wash_format: WashFormat = "Plate",
    pre_dispense_before_volume: int = 10,
    pre_dispense_before_count: int = 2,
    dispense: SyringeDispense | None = None,
    aspirate: ManifoldAspirate | None = None,
    stages: WashStages | None = None,
    shake_soak: ShakeSoak | None = None,
    final_aspirate: ManifoldAspirate | None = None,
  ) -> None:
    """Wash a 1536-well plate, refilling the wells from a syringe rather than from the manifold.

    A separate step rather than a plate-dependent :meth:`wash`: it is dispensed by different
    hardware, carries no bottom wash, and selects wells on its dispense.

    Args:
      cycles: How many wash cycles to run.
      wash_format: Whether to wash the whole plate, selected sectors or selected strips.
      pre_dispense_before_volume: Volume per well in µL to pre-dispense before washing starts.
      pre_dispense_before_count: How many times to pre-dispense before washing starts.
      dispense: The syringe dispense that refills the well each cycle.
      aspirate: The aspirate that empties the well at the start of each cycle.
      stages: Which optional stages run.
      shake_soak: The pause after each dispense.
      final_aspirate: The aspirate that empties the well after the last cycle.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = Wash1536(
      cycles=cycles,
      wash_format=wash_format,
      pre_dispense_before_volume=pre_dispense_before_volume,
      pre_dispense_before_count=pre_dispense_before_count,
    )
    if dispense is not None:
      step.dispense = dispense
    if aspirate is not None:
      step.aspirate = aspirate
    if stages is not None:
      step.stages = stages
    if shake_soak is not None:
      step.shake_soak = shake_soak
    if final_aspirate is not None:
      step.final_aspirate = final_aspirate
    await run_steps(self._runtime, [step])

  async def strip_wash(
    self,
    cycles: int = 3,
    wash_format: WashFormat = "Plate",
    dispense: StripDispense | None = None,
    aspirate: StripAspirate | None = None,
    stages: WashStages | None = None,
    shake_soak: ShakeSoak | None = None,
    bottom_wash: StripDispense | None = None,
    final_aspirate: StripAspirate | None = None,
    columns: WellMask | None = None,
    rows: WellMask | None = None,
  ) -> None:
    """Wash the plate through the strip washer manifold.

    Args:
      cycles: How many wash cycles to run.
      wash_format: Whether to wash the whole plate, selected sectors or selected strips.
      dispense: The dispense that refills the well each cycle.
      aspirate: The aspirate that empties the well at the start of each cycle.
      stages: Which optional stages run.
      shake_soak: The pause after each dispense.
      bottom_wash: The dispense that washes the bottom of the well, when that stage runs.
      final_aspirate: The aspirate that empties the well after the last cycle.
      columns: Which columns to wash.
      rows: Which rows to wash.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = StripWash(cycles=cycles, wash_format=wash_format)
    if dispense is not None:
      step.dispense = dispense
    if aspirate is not None:
      step.aspirate = aspirate
    if stages is not None:
      step.stages = stages
    if shake_soak is not None:
      step.shake_soak = shake_soak
    if bottom_wash is not None:
      step.bottom_wash = bottom_wash
    if final_aspirate is not None:
      step.final_aspirate = final_aspirate
    if columns is not None:
      step.columns = columns
    if rows is not None:
      step.rows = rows
    await run_steps(self._runtime, [step])

  async def strip_aspirate(
    self,
    travel_rate: TravelRate = "3",
    delay: int = 0,
    positioning: Positioning | None = None,
    secondary: SecondaryAspirate | None = None,
    columns: WellMask | None = None,
    rows: WellMask | None = None,
  ) -> None:
    """Draw the wells empty through the strip washer manifold.

    Args:
      travel_rate: How fast the tips descend into the well. The strip washer offers two rates the
        wash manifold does not.
      delay: How long to keep aspirating once the tips are down, in ms.
      positioning: Where in the well to aspirate.
      secondary: Whether to aspirate a second time, in what pattern and where.
      columns: Which columns to aspirate.
      rows: Which rows to aspirate.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = StripAspirate(travel_rate=travel_rate, delay=delay)
    if positioning is not None:
      step.positioning = positioning
    if secondary is not None:
      step.secondary = secondary
    if columns is not None:
      step.columns = columns
    if rows is not None:
      step.rows = rows
    await run_steps(self._runtime, [step])

  async def strip_dispense(
    self,
    volume: int,
    flow_rate: int = 5,
    positioning: Positioning | None = None,
    pre_dispense: PreDispense | None = None,
    vacuum: VacuumDelay | None = None,
    columns: WellMask | None = None,
    rows: WellMask | None = None,
  ) -> None:
    """Dispense into every selected well through the strip washer manifold.

    Args:
      volume: Volume per well in µL.
      flow_rate: How fast to dispense.
      positioning: Where in the well to dispense.
      pre_dispense: Whether to pre-dispense first, at what volume, rate and how many times.
      vacuum: Whether to hold the vacuum off until a volume has been dispensed.
      columns: Which columns to dispense into.
      rows: Which rows to dispense into.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = StripDispense(volume=volume, flow_rate=flow_rate)
    if positioning is not None:
      step.positioning = positioning
    if pre_dispense is not None:
      step.pre_dispense = pre_dispense
    if vacuum is not None:
      step.vacuum = vacuum
    if columns is not None:
      step.columns = columns
    if rows is not None:
      step.rows = rows
    await run_steps(self._runtime, [step])

  async def strip_prime(
    self,
    volume: int = 5_000,
    flow_rate: int = 5,
    cycles: int = 2,
    submerge: Submerge | None = None,
  ) -> None:
    """Pump fluid through the strip washer manifold until its lines are full.

    Args:
      volume: Volume to pump in µL. What the manifold accepts depends on which one is fitted.
      flow_rate: How fast to pump.
      cycles: How many prime cycles to run.
      submerge: Whether to leave the tips in fluid afterwards, and for how long.

    Raises:
      BiotekError: If the step cannot run, or fails while running.
    """
    step = StripPrime(volume=volume, flow_rate=flow_rate, cycles=cycles)
    if submerge is not None:
      step.submerge = submerge
    await run_steps(self._runtime, [step])
