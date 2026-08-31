"""What a user holds: one class per model, and the capability objects it exposes.

Each model is built against a fake instrument, so setup, the plate, the palette and the capability
objects are exercised without hardware. What a capability method does is one step run as a one-step
protocol, and that is what is checked here -- the payloads themselves are the cross-reference's job.
"""

from __future__ import annotations

import unittest

from pylabrobot.agilent.biotek.lhc import EL406, MultiFlo, MultiFloFX, Washer405TS
from pylabrobot.agilent.biotek.lhc.devices.components.peristaltic_dispenser import (
  PeristalticDispenser,
)
from pylabrobot.agilent.biotek.lhc.devices.components.syringe_dispenser import SyringeDispenser
from pylabrobot.agilent.biotek.lhc.devices.components.washer import PlateWasher
from pylabrobot.agilent.biotek.lhc.devices.instrument_settings import InstrumentSettings
from pylabrobot.agilent.biotek.lhc.enums.instrument.instrument_family import InstrumentFamily
from pylabrobot.agilent.biotek.lhc.enums.plates.plate_type import PlateType
from pylabrobot.agilent.biotek.lhc.enums.steps.step_action import StepAction
from pylabrobot.agilent.biotek.lhc.enums.steps.step_type import StepType
from pylabrobot.agilent.biotek.lhc.protocols.protocol import Protocol, ProtocolEntry
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.manifold_prime import ManifoldPrime
from pylabrobot.agilent.biotek.lhc.serialization.command_numbers import CommandNumber
from pylabrobot.agilent.biotek.lhc.tests.helpers import (
  ACCEPTS_EVERY_PLATE,
  FakeInstrument,
  make_plate,
)

ANSWERS = {
  CommandNumber.GET_SYRINGE_MANIFOLD_INSTALLED: bytes([1]),
  CommandNumber.GET_SYRINGE_BOX_INFO: bytes([1, 2]),
  CommandNumber.GET_SELECTED_PERI_INSTALLED: bytes([1]),
  CommandNumber.GET_WASHER_MANIFOLD_INSTALLED: bytes([0]),
  CommandNumber.GET_EXT_VALVE_MODULE_INSTALLED: bytes([1]),
  CommandNumber.GET_VACUUM_FILTRATION_INSTALLED: bytes([0]),
  CommandNumber.GET_ULTRASONIC_CLEANER_INSTALLED: bytes([1]),
  CommandNumber.GET_CELL_WASHING_INSTALLED: bytes([1]),
  CommandNumber.GET_IS_PERI_HALF_UL_SUPPORTED: bytes([1]),
  CommandNumber.GET_Y_AXIS_INSTALLED: bytes([1]),
  CommandNumber.GET_SERIAL_NUMBER: b"SN0001".ljust(24),
  CommandNumber.GET_BASECODE_VERSION: (
    b"7100000" + b"2.22.6  " + b"ABCD" + b"DCBA" + b"1.000" + b"1.0" + b"2.0" + b" " * 12
  ),
  CommandNumber.IS_STRIP_WASHER_BOX_CONNECTED: bytes([0]),
  CommandNumber.GET_STRIP_WASHER_HW_INSTALLED: bytes([0]),
  CommandNumber.GET_WHICH_BASECODE_IS_INSTALLED: bytes([0]),
  CommandNumber.GET_FLUID_TRACKING_ENABLED: bytes([1]),
  **ACCEPTS_EVERY_PLATE,
}
"""What the fake instrument answers, which is a fully equipped instrument of the original model."""


class DeviceTestCase(unittest.IsolatedAsyncioTestCase):
  """A model built onto a fake instrument."""

  async def build(self, cls, wells: int = 96, answers: dict | None = None):
    """Build a model, set it up and give it a plate.

    Args:
      cls: Which model to build.
      wells: How many wells the plate has.
      answers: What the instrument answers, defaulting to a fully equipped one.

    Returns:
      The device and the fake instrument behind it.
    """
    io = FakeInstrument(answers=ANSWERS if answers is None else answers)
    device = cls(port="fake", io=io)
    # The fake instrument answers at once, so none of the pacing a real one needs is wanted here.
    device.settle = 0
    await device.setup()
    device.set_plate(make_plate(wells))
    return device, io


class TestTheLifecycle(DeviceTestCase):
  """Opening a device, and what it learns while doing so."""

  async def test_setup_reads_what_is_fitted(self):
    device, _ = await self.build(EL406)
    self.assertIs(device.settings.family, InstrumentFamily.EL406)
    self.assertTrue(device.settings.peri_pump)

  async def test_setup_proves_something_is_listening_before_reading_anything(self):
    _, io = await self.build(EL406)
    self.assertEqual(io.sent[0], int(CommandNumber.PING))

  async def test_a_device_reports_its_own_name(self):
    device, _ = await self.build(EL406)
    self.assertEqual(device.name, "EL406")

  async def test_stopping_closes_the_link(self):
    device, io = await self.build(EL406)
    await device.stop()
    self.assertFalse(io.is_open)

  async def test_the_serial_number_and_the_firmware_can_be_read(self):
    device, _ = await self.build(EL406)
    self.assertEqual(await device.get_serial_number(), "SN0001")
    self.assertEqual((await device.get_firmware_version()).software_version.strip(), "2.22.6")


class TestThePlate(DeviceTestCase):
  """Telling a device what is on its carrier."""

  async def test_a_plate_is_resolved_to_a_format_the_model_works(self):
    device, _ = await self.build(EL406)
    self.assertIsNotNone(device.plate)
    self.assertIs(device.plate.plate_type, PlateType.PLATE_96_WELL)

  async def test_a_format_can_be_named_outright(self):
    device, _ = await self.build(EL406)
    device.set_plate(make_plate(384), plate_type=PlateType.PLATE_384_WELL_PCR)
    self.assertIs(device.plate.plate_type, PlateType.PLATE_384_WELL_PCR)

  async def test_a_plate_the_model_does_not_work_is_an_error_naming_what_it_does(self):
    device, _ = await self.build(Washer405TS)
    with self.assertRaisesRegex(ValueError, "it offers"):
      device.set_plate(make_plate(6))

  async def test_forgetting_the_plate_stops_everything(self):
    device, _ = await self.build(EL406)
    device.clear_plate()
    self.assertIsNone(device.plate)
    with self.assertRaises(Exception):
      await device.run_step(ManifoldPrime())


class TestThePalette(DeviceTestCase):
  """What a model offers, which is its own list narrowed by what is fitted."""

  async def test_a_wash_only_model_offers_no_dispensing(self):
    device, _ = await self.build(Washer405TS)
    offered = device.get_available_steps()
    self.assertIn(StepType.MANIFOLD_WASH, offered)
    self.assertNotIn(StepType.SYRINGE_DISPENSE, offered)
    self.assertNotIn(StepType.PERI_DISPENSE, offered)

  async def test_a_dispenser_only_model_offers_no_washing(self):
    device, _ = await self.build(MultiFlo)
    offered = device.get_available_steps()
    self.assertIn(StepType.PERI_DISPENSE, offered)
    self.assertNotIn(StepType.MANIFOLD_WASH, offered)

  async def test_hardware_that_is_not_fitted_is_not_offered(self):
    """The instrument reporting no peristaltic pump takes those step types out of the palette."""
    answers = dict(ANSWERS)
    answers[CommandNumber.GET_SELECTED_PERI_INSTALLED] = bytes([0])
    device, _ = await self.build(EL406, answers=answers)
    self.assertFalse(device.settings.peri_pump)
    self.assertNotIn(StepType.PERI_DISPENSE, device.get_available_steps())

  async def test_the_palette_is_in_the_order_the_model_offers_them(self):
    """Not the order the types are numbered: a model lists what it is for first, which is what a
    user reading the palette wants to see."""
    device, _ = await self.build(EL406)
    offered = device.get_available_steps()
    self.assertEqual(offered[0], StepType.MANIFOLD_WASH)
    self.assertNotEqual(offered, sorted(offered, key=lambda member: member.value))
    self.assertEqual(len(set(offered)), len(offered))


class TestTheCapabilityObjects(DeviceTestCase):
  """Which capability objects each model exposes, and what calling one does."""

  async def test_a_wash_only_model_exposes_only_a_washer(self):
    device, _ = await self.build(Washer405TS)
    self.assertIsInstance(device.washer, PlateWasher)
    with self.assertRaises(AttributeError):
      device.syringe_dispenser  # noqa: B018 - the point is that it is not there

  async def test_a_dispenser_only_model_exposes_no_washer(self):
    device, _ = await self.build(MultiFlo)
    self.assertIsInstance(device.syringe_dispenser, SyringeDispenser)
    self.assertIsInstance(device.peristaltic_dispenser, PeristalticDispenser)
    with self.assertRaises(AttributeError):
      device.washer  # noqa: B018 - the point is that it is not there

  async def test_the_newest_model_exposes_all_three(self):
    device, _ = await self.build(MultiFloFX)
    self.assertIsInstance(device.washer, PlateWasher)
    self.assertIsInstance(device.syringe_dispenser, SyringeDispenser)
    self.assertIsInstance(device.peristaltic_dispenser, PeristalticDispenser)

  async def test_one_call_brackets_itself_in_a_batch(self):
    device, io = await self.build(EL406)
    await device.washer.prime(volume=40_000)
    self.assertEqual(io.sent.count(int(CommandNumber.INIT_PROTOCOL)), 1)
    self.assertEqual(io.sent.count(int(CommandNumber.EXIT_PROTOCOL)), 1)
    self.assertIn(int(CommandNumber.MANIFOLD_PRIME), io.sent)

  async def test_several_calls_in_one_batch_share_the_opening(self):
    device, io = await self.build(EL406)
    async with device.batch():
      await device.washer.prime(volume=40_000)
      await device.washer.auto_clean(duration=60)
    self.assertEqual(io.sent.count(int(CommandNumber.INIT_PROTOCOL)), 1)
    self.assertEqual(io.sent.count(int(CommandNumber.EXIT_PROTOCOL)), 1)

  async def test_a_capability_method_sends_the_step_it_names(self):
    device, io = await self.build(EL406)
    await device.washer.dispense(volume=100, buffer="B", flow_rate=5)
    self.assertIn(int(CommandNumber.MANIFOLD_DISPENSE), io.sent)


class TestRunningAProtocol(DeviceTestCase):
  """Handing a device a whole protocol rather than one operation."""

  async def test_a_list_of_steps_runs_in_one_batch(self):
    device, io = await self.build(EL406)
    await device.run_protocol([ManifoldPrime(volume=40_000), ManifoldPrime(volume=10_000)])
    self.assertEqual(io.sent.count(int(CommandNumber.INIT_PROTOCOL)), 1)
    self.assertEqual(io.sent.count(int(CommandNumber.MANIFOLD_PRIME)), 2)

  async def test_a_protocol_object_has_its_steps_built_from_its_entries(self):
    device, io = await self.build(EL406)
    protocol = Protocol(
      entries=[
        ProtocolEntry(
          action=StepAction.CUSTOM,
          step_type=StepType.MANIFOLD_PRIME,
          definition="DV103|9|A|40|9|True|5|False|00:05",
        )
      ]
    )
    await device.run_protocol(protocol)
    self.assertIn(int(CommandNumber.MANIFOLD_PRIME), io.sent)

  async def test_the_check_can_be_asked_for_on_its_own(self):
    device, _ = await self.build(EL406)
    self.assertTrue(await device.can_run([ManifoldPrime(volume=40_000)]))

  async def test_a_step_built_outright_can_be_run(self):
    device, io = await self.build(EL406)
    await device.run_step(ManifoldPrime(volume=40_000))
    self.assertIn(int(CommandNumber.MANIFOLD_PRIME), io.sent)


class TestTheServiceSurface(DeviceTestCase):
  """The operations that are about the instrument rather than about liquid."""

  async def test_resetting_sends_its_own_command(self):
    device, io = await self.build(EL406)
    await device.reset()
    self.assertIn(int(CommandNumber.RESET_INSTRUMENT), io.sent)

  async def test_homing_everything_is_the_default(self):
    device, io = await self.build(EL406)
    await device.home()
    self.assertIn(int(CommandNumber.HOME_VERIFY_MOTORS), io.sent)

  async def test_the_self_check_sends_its_own_command(self):
    device, io = await self.build(EL406)
    await device.self_check()
    self.assertIn(int(CommandNumber.RUN_SELF_CHECK), io.sent)

  async def test_shaking_runs_as_a_step(self):
    device, io = await self.build(EL406)
    await device.shake(duration=5, soak_duration=30)
    self.assertIn(int(CommandNumber.SHAKE_SOAK), io.sent)


class TestComparingWhatAProtocolExpects(DeviceTestCase):
  """The one use a protocol's declared options are put to, and only when asked."""

  async def test_a_settings_record_can_be_compared_directly(self):
    device, _ = await self.build(EL406)
    self.assertTrue(device.compare_settings(device.settings))

  async def test_a_protocol_without_a_document_is_an_explicit_error(self):
    device, _ = await self.build(EL406)
    with self.assertRaisesRegex(ValueError, "no fitted-options document"):
      device.compare_settings(Protocol(protocol_name="rinse"))

  async def test_a_protocol_written_for_another_instrument_still_runs(self):
    """The comparison is never consulted on the way to running something: a protocol is measured
    against the instrument as it is, which is what the check does."""
    device, io = await self.build(EL406)
    declared = InstrumentSettings(family=InstrumentFamily.MULTIFLO_FX)
    self.assertFalse(device.compare_settings(declared))
    await device.run_protocol([ManifoldPrime(volume=40_000)])
    self.assertIn(int(CommandNumber.MANIFOLD_PRIME), io.sent)
