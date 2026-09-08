"""What an observer is told, and that being watched changes nothing.

Two things have to hold for an observer to be worth anything. It must see every frame, attributed
to the operation that caused it, so that a session can be replayed or checked against another
implementation of the same wire format. And it must be unable to affect the link: an observer that
raises, or that is simply absent, has to leave the exchange exactly as it was.
"""

from __future__ import annotations

import unittest

from pylabrobot.agilent.biotek.lhc.comm.observer import (
  LinkObserver,
  Operation,
  Session,
  SessionRecorder,
)
from pylabrobot.agilent.biotek.lhc.devices.el406 import EL406
from pylabrobot.agilent.biotek.lhc.enums.motion.motor import Motor
from pylabrobot.agilent.biotek.lhc.enums.motion.motor_home_type import MotorHomeType
from pylabrobot.agilent.biotek.lhc.error_handling import BiotekError
from pylabrobot.agilent.biotek.lhc.protocols.steps.step_parts.groups import Shake, Soak
from pylabrobot.agilent.biotek.lhc.protocols.steps.steps.shake_soak import ShakeSoak
from pylabrobot.agilent.biotek.lhc.serialization.command_numbers import CommandNumber
from pylabrobot.agilent.biotek.lhc.serialization.frame import HEADER_LENGTH, Header
from pylabrobot.agilent.biotek.lhc.tests.helpers import PUMP_READY, FakeInstrument, make_plate


def a_step() -> ShakeSoak:
  """A step every model can run, for a test that only cares that one was run.

  Returns:
    The step.
  """
  return ShakeSoak(shake=Shake(enabled=True), soak=Soak(enabled=False))


class Raiser(SessionRecorder):
  """An observer that fails at everything it is asked to do."""

  async def operation_started(self, operation: Operation) -> None:
    """Fail.

    Args:
      operation: Ignored.

    Raises:
      RuntimeError: Always.
    """
    raise RuntimeError("started")

  async def operation_finished(self, operation: Operation, failure: BaseException | None) -> None:
    """Fail.

    Args:
      operation: Ignored.
      failure: Ignored.

    Raises:
      RuntimeError: Always.
    """
    raise RuntimeError("finished")

  async def frame_sent(self, frame: bytes) -> None:
    """Fail.

    Args:
      frame: Ignored.

    Raises:
      RuntimeError: Always.
    """
    raise RuntimeError("sent")

  async def frame_received(self, header: bytes, payload: bytes) -> None:
    """Fail.

    Args:
      header: Ignored.
      payload: Ignored.

    Raises:
      RuntimeError: Always.
    """
    raise RuntimeError("received")


class ObserverTestCase(unittest.IsolatedAsyncioTestCase):
  """An instrument that is not there, with somewhere to attach an observer."""

  async def built(self, observer: LinkObserver | None, **kwargs) -> EL406:
    """Build a watched instrument and set it up.

    Args:
      observer: What to watch the link with, or None to watch nothing.
      **kwargs: Passed to the fake instrument, which is kept as ``self.fake``.

    Returns:
      The device, already set up.
    """
    kwargs.setdefault("answers", PUMP_READY)
    self.fake = FakeInstrument(**kwargs)
    device = EL406(io=self.fake, observer=observer)
    device.settle = 0
    await device.setup()
    return device

  @staticmethod
  def numbers(session: Session) -> list[int]:
    """The command number of every frame an operation sent.

    Args:
      session: The completed session.

    Returns:
      The numbers, in the order they went out.
    """
    return [Header.from_bytes(frame[:HEADER_LENGTH]).number for frame in session.sent]

  @staticmethod
  def named(recorder: SessionRecorder, name: str) -> list[Session]:
    """Every session of one operation.

    Args:
      recorder: What collected them.
      name: Which operation to pick out.

    Returns:
      Those sessions, in order.
    """
    return [session for session in recorder.sessions if session.operation.name == name]


class TestWhatIsReported(ObserverTestCase):
  """Which frames land in which operation."""

  async def test_setup_reports_a_ping_and_one_settings_read(self):
    recorder = SessionRecorder()
    await self.built(recorder)
    self.assertEqual(
      [session.operation.name for session in recorder.sessions], ["ping", "read settings"]
    )
    # The ping is two frames: proving something is listening, then reading what it is.
    self.assertEqual(
      self.numbers(recorder.sessions[0]),
      [CommandNumber.PING, CommandNumber.GET_BASECODE_VERSION],
    )
    self.assertGreater(len(self.numbers(recorder.sessions[1])), 5)

  async def test_every_frame_carries_its_reply(self):
    recorder = SessionRecorder()
    device = await self.built(recorder)
    await device.get_serial_number()
    exchange = self.named(recorder, "serial number")[0].exchanges[0]
    self.assertEqual(
      Header.from_bytes(exchange.sent[:HEADER_LENGTH]).number, CommandNumber.GET_SERIAL_NUMBER
    )
    self.assertEqual(len(exchange.header), HEADER_LENGTH)
    self.assertEqual(exchange.received, exchange.header + exchange.payload)

  async def test_a_step_run_reports_the_step_it_ran(self):
    recorder = SessionRecorder()
    device = await self.built(recorder)
    device.set_plate(make_plate())
    step = a_step()
    await device.run_step(step)
    runs = self.named(recorder, "run step")
    self.assertEqual(len(runs), 1)
    self.assertIs(runs[0].operation.step, step)
    self.assertEqual(self.numbers(runs[0]), [CommandNumber.SHAKE_SOAK])

  async def test_opening_a_batch_is_one_operation(self):
    recorder = SessionRecorder()
    device = await self.built(recorder)
    device.set_plate(make_plate())
    async with device.batch():
      pass
    self.assertEqual(
      self.numbers(self.named(recorder, "open batch")[0]), [CommandNumber.INIT_PROTOCOL]
    )
    self.assertEqual(
      self.numbers(self.named(recorder, "close batch")[0]), [CommandNumber.EXIT_PROTOCOL]
    )
    self.assertEqual(self.named(recorder, "home"), [])

  async def test_homing_on_close_is_its_own_operation(self):
    recorder = SessionRecorder()
    device = await self.built(recorder)
    device.set_plate(make_plate())
    async with device.batch(home_on_close=True):
      pass
    home = self.named(recorder, "home")[0]
    self.assertEqual(
      home.operation.arguments, (int(MotorHomeType.HOME_XYZ_MOTORS), int(Motor.CARRIER_X))
    )
    self.assertEqual(self.numbers(home), [CommandNumber.HOME_VERIFY_MOTORS])

  async def test_status_polls_are_reported_one_operation_each(self):
    recorder = SessionRecorder()
    device = await self.built(recorder, busy_polls=3)
    device.set_plate(make_plate())
    await device.run_step(a_step())
    polls = self.named(recorder, "status")
    self.assertGreater(len(polls), 1)
    for poll in polls:
      self.assertEqual(self.numbers(poll), [CommandNumber.GET_PROTOCOL_STATUS])

  async def test_a_failed_operation_reports_what_failed(self):
    recorder = SessionRecorder()
    device = await self.built(recorder)
    self.fake.status = 24578
    with self.assertRaises(BiotekError):
      await device.get_serial_number()
    self.assertIsNotNone(self.named(recorder, "serial number")[0].failure)

  async def test_an_observer_can_be_attached_after_the_device_is_built(self):
    device = await self.built(None)
    recorder = SessionRecorder()
    device._runtime.link.observer = recorder  # noqa: SLF001 -- the seam a harness attaches to.
    await device.get_serial_number()
    self.assertEqual([session.operation.name for session in recorder.sessions], ["serial number"])


class TestBeingWatchedChangesNothing(ObserverTestCase):
  """A watched run and an unwatched one put the same bytes on the wire."""

  async def a_run(self, observer: LinkObserver | None) -> tuple[list[int], list[bytes]]:
    """Run a step inside a batch and report what went out.

    Args:
      observer: What to watch the link with, or None.

    Returns:
      Every command number written, and every payload.
    """
    device = await self.built(observer)
    device.set_plate(make_plate())
    async with device.batch():
      await device.run_step(a_step())
    return list(self.fake.sent), list(self.fake.payloads)

  async def test_an_observer_sees_the_frames_and_adds_none(self):
    watched = await self.a_run(SessionRecorder())
    self.assertEqual(watched, await self.a_run(None))

  async def test_an_observer_that_raises_is_ignored(self):
    watched = await self.a_run(Raiser())
    self.assertEqual(watched, await self.a_run(None))


if __name__ == "__main__":
  unittest.main()
