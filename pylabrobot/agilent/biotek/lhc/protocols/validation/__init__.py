"""Whether a protocol can run, and what it requires of the instrument if it does."""

from __future__ import annotations

from pylabrobot.agilent.biotek.lhc.protocols.validation.protocol_pass import validate
from pylabrobot.agilent.biotek.lhc.protocols.validation.report import (
  Rejection,
  StepReport,
  ValidationReport,
)
from pylabrobot.agilent.biotek.lhc.protocols.validation.reservations import Reservations

__all__ = ["Rejection", "Reservations", "StepReport", "ValidationReport", "validate"]
