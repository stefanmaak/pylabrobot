"""What an observer is told, and that being watched changes nothing.

Two things have to hold for an observer to be worth anything. It must see every frame, attributed
to the operation that caused it, so that a session can be replayed or checked against another
implementation of the same wire format. And it must be unable to affect the link: an observer that
raises, or that is simply absent, has to leave the exchange exactly as it was.
"""

from __future__ import annotations

import asyncio
import unittest
from contextlib import suppress

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


_STARTUP_POLLS = 100
"""How many turns of the loop to give a step to reach the wire before calling it stuck."""


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


class TestTwoCallersAtOnce(unittest.IsolatedAsyncioTestCase):
  """Which operation a frame belongs to when two of them overlap.

  A step is polled by the task that ran it, and pausing, resuming or aborting it comes from another
  task while those polls are going out. Every frame has to land in the session of the operation
  that sent it, or a recording cannot be replayed and a comparison measures the wrong frames
  against the wrong call. The recorder is driven directly here: the interleaving is the whole
  point, so it is written out rather than left to the scheduler.
  """

  @staticmethod
  def names(recorder: SessionRecorder) -> list[str]:
    """Which operations a recorder collected.

    Args:
      recorder: What collected them.

    Returns:
      The names, in the order the sessions finished.
    """
    return [session.operation.name for session in recorder.sessions]

  async def test_an_operation_inside_another_callers_is_its_own_session(self):
    recorder = SessionRecorder()
    polling, released = asyncio.Event(), asyncio.Event()

    async def poll() -> None:
      """Send a status poll that is still open when the other caller aborts."""
      await recorder.operation_started(Operation("status"))
      await recorder.frame_sent(b"poll")
      polling.set()
      await released.wait()
      await recorder.frame_received(b"reply", b"")
      await recorder.operation_finished(Operation("status"), None)

    poller = asyncio.create_task(poll())
    await polling.wait()
    await recorder.operation_started(Operation("abort"))
    await recorder.frame_sent(b"abort")
    await recorder.operation_finished(Operation("abort"), None)
    released.set()
    await poller

    self.assertEqual(self.names(recorder), ["abort", "status"])
    self.assertEqual(recorder.sessions[0].sent, [b"abort"])
    self.assertEqual(recorder.sessions[1].sent, [b"poll"])

  async def test_a_reply_lands_on_the_frame_its_own_caller_sent(self):
    recorder = SessionRecorder()
    polling, released = asyncio.Event(), asyncio.Event()

    async def poll() -> None:
      """Send a status poll whose reply comes back after the other caller has been and gone."""
      await recorder.operation_started(Operation("status"))
      await recorder.frame_sent(b"poll")
      polling.set()
      await released.wait()
      await recorder.frame_received(b"poll reply", b"")
      await recorder.operation_finished(Operation("status"), None)

    poller = asyncio.create_task(poll())
    await polling.wait()
    await recorder.operation_started(Operation("abort"))
    await recorder.frame_sent(b"abort")
    await recorder.frame_received(b"abort reply", b"")
    await recorder.operation_finished(Operation("abort"), None)
    released.set()
    await poller

    self.assertEqual(recorder.sessions[0].exchanges[0].received, b"abort reply")
    self.assertEqual(recorder.sessions[1].exchanges[0].received, b"poll reply")

  async def test_nesting_in_one_caller_is_still_one_session(self):
    recorder = SessionRecorder()
    await recorder.operation_started(Operation("run step"))
    await recorder.operation_started(Operation("status"))
    await recorder.frame_sent(b"inner")
    await recorder.operation_finished(Operation("status"), None)
    await recorder.operation_finished(Operation("run step"), None)
    self.assertEqual(self.names(recorder), ["run step"])
    self.assertEqual(recorder.sessions[0].sent, [b"inner"])

  async def test_a_caller_is_forgotten_once_its_operation_closes(self):
    recorder = SessionRecorder()
    for _ in range(3):
      await recorder.operation_started(Operation("status"))
      await recorder.operation_finished(Operation("status"), None)
    self.assertEqual(len(recorder.sessions), 3)
    self.assertFalse(recorder._open)
    self.assertFalse(recorder._depth)


class TestRunControlWhileAStepRuns(ObserverTestCase):
  """What the recorder ends up holding when a running step is paused, resumed or aborted."""

  async def running_step(self, recorder: SessionRecorder):
    """A device with a step that has been sent and reports itself running forever.

    Args:
      recorder: What is watching the link.

    Returns:
      The device and the task running the step, which the caller stops when done with it.
    """
    device = await self.built(recorder, busy_after_step=True)
    device.set_plate(make_plate())
    running = asyncio.create_task(device.run_step(a_step()))
    for _ in range(_STARTUP_POLLS):
      if self.named(recorder, "run step"):
        return device, running
      await asyncio.sleep(0)
    running.cancel()
    self.fail("the step never reached the wire")

  @staticmethod
  async def stopped(running: asyncio.Task) -> None:
    """Stop waiting for a step that never finishes.

    Args:
      running: The task running it.
    """
    running.cancel()
    with suppress(asyncio.CancelledError):
      await running

  async def test_a_pause_is_its_own_operation(self):
    recorder = SessionRecorder()
    device, running = await self.running_step(recorder)
    await device.pause()
    await self.stopped(running)
    paused = self.named(recorder, "pause")
    self.assertEqual(len(paused), 1)
    self.assertEqual(self.numbers(paused[0]), [CommandNumber.PAUSE_STEP])

  async def test_a_resume_is_its_own_operation(self):
    recorder = SessionRecorder()
    device, running = await self.running_step(recorder)
    await device.pause()
    await device.resume()
    await self.stopped(running)
    resumed = self.named(recorder, "resume")
    self.assertEqual(len(resumed), 1)
    self.assertEqual(self.numbers(resumed[0]), [CommandNumber.RESUME_STEP])

  async def test_an_abort_is_its_own_operation(self):
    recorder = SessionRecorder()
    device, running = await self.running_step(recorder)
    await device.abort()
    await self.stopped(running)
    aborted = self.named(recorder, "abort")
    self.assertEqual(len(aborted), 1)
    self.assertEqual(self.numbers(aborted[0]), [CommandNumber.ABORT_STEP])

  async def test_the_polls_alongside_them_hold_nothing_else(self):
    recorder = SessionRecorder()
    device, running = await self.running_step(recorder)
    await device.abort()
    await self.stopped(running)
    polls = self.named(recorder, "status")
    self.assertTrue(polls)
    for poll in polls:
      self.assertEqual(self.numbers(poll), [CommandNumber.GET_PROTOCOL_STATUS])


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
