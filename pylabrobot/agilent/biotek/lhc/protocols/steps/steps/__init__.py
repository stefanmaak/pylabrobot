"""One module per step type.

Every class here is a step, named for the operation it performs.
"""

from __future__ import annotations

from pylabrobot.agilent.biotek.lhc.enums.steps.step_type import StepType
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_interface import Step
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_aspirate import ManifoldAspirate
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_auto_clean import (
  ManifoldAutoClean,
)
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_dispense import ManifoldDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_prime import ManifoldPrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_wash import ManifoldWash
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.peri_dispense import PeriDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.peri_prime import PeriPrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.peri_purge import PeriPurge
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.peri_wash_aspirate import PeriWashAspirate
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.peri_wash_dispense import PeriWashDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.shake_soak import ShakeSoak
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_aspirate import StripAspirate
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_dispense import StripDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_prime import StripPrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.strip_wash import StripWash
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.syringe_dispense import SyringeDispense
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.syringe_prime import SyringePrime
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.wash_1536 import Wash1536

STEP_CLASSES: dict[StepType, type[Step]] = {
  StepType.PERI_DISPENSE: PeriDispense,
  StepType.PERI_PRIME: PeriPrime,
  StepType.PERI_PURGE: PeriPurge,
  StepType.SYRINGE_DISPENSE: SyringeDispense,
  StepType.SYRINGE_PRIME: SyringePrime,
  StepType.MANIFOLD_WASH: ManifoldWash,
  StepType.MANIFOLD_ASPIRATE: ManifoldAspirate,
  StepType.MANIFOLD_DISPENSE: ManifoldDispense,
  StepType.MANIFOLD_PRIME: ManifoldPrime,
  StepType.MANIFOLD_AUTO_CLEAN: ManifoldAutoClean,
  StepType.SHAKE_SOAK: ShakeSoak,
  StepType.WASH_1536: Wash1536,
  StepType.STRIP_WASH: StripWash,
  StepType.STRIP_ASPIRATE: StripAspirate,
  StepType.STRIP_DISPENSE: StripDispense,
  StepType.STRIP_PRIME: StripPrime,
  StepType.PERI_WASH_ASPIRATE: PeriWashAspirate,
  StepType.PERI_WASH_DISPENSE: PeriWashDispense,
}
"""Which class implements each step type."""

__all__ = [
  "STEP_CLASSES",
  "ManifoldAspirate",
  "ManifoldAutoClean",
  "ManifoldDispense",
  "ManifoldPrime",
  "ManifoldWash",
  "PeriDispense",
  "PeriPrime",
  "PeriPurge",
  "PeriWashAspirate",
  "PeriWashDispense",
  "ShakeSoak",
  "StripAspirate",
  "StripDispense",
  "StripPrime",
  "StripWash",
  "SyringeDispense",
  "SyringePrime",
  "Wash1536",
]
