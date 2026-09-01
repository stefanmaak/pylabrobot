"""Watching what a link does, without changing what it does.

A :class:`Link` moves frames; nothing above it sees them, and nothing below it knows why they were
sent. An observer is given both: the operation the device was asked to carry out, and every frame
that went out or came back while it was being carried out. That is enough to record a session, to
replay one, or to check a run against an independent implementation of the same wire format.

An observer never changes an exchange. It is told what happened after it happened, its exceptions
are logged rather than raised, and a link with no observer does exactly what it did before.
"""

from __future__ import annotations

import abc
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator, Literal

if TYPE_CHECKING:  # pragma: no cover -- import cycle: a step is what an operation may carry.
  from pylabrobot.agilent.biotek.lhc.protocols.steps.step_interface import Step

logger = logging.getLogger(__name__)

OperationName = Literal[
  "ping",
  "read settings",
  "check protocol",
  "open batch",
  "close batch",
  "run step",
  "status",
  "abort",
  "pause",
  "resume",
  "plate restriction",
  "carrier type",
  "serial number",
  "firmware version",
  "self check",
  "reset",
  "home",
]
"""What a device can be asked to do, as one name per bracketed block of frames.

An operation is coarser than a command: opening a batch reconciles the peristaltic hardware before
it sends the one command that opens it, and reading the fitted options is twenty queries. The name
is what the block is for, not what any one frame in it is.
"""


@dataclass(frozen=True)
class Operation:
  """One thing a device was asked to do.

  Attributes:
    name: What was asked for.
    step: The step being run, on the operation that runs one, and None on every other.
    steps: The steps being checked, on the operation that checks a protocol, and empty on every
      other. A check is not only a check -- it works out what the protocol requires of the pumps,
      and opening a batch is what makes the hardware match -- so anything reproducing a run has to
      reproduce the check with the same steps, in the same order.
    arguments: The values the operation was asked with, for operations that take any.
  """

  name: OperationName
  step: Step | None = None
  steps: tuple[Step, ...] = ()
  arguments: tuple[int, ...] = ()


@dataclass
class Exchange:
  """One frame sent and what came back for it.

  Attributes:
    sent: The frame that went out, header and payload.
    header: The reply header, or empty when nothing came back.
    payload: The reply payload, or empty when nothing came back.
  """

  sent: bytes
  header: bytes = b""
  payload: bytes = b""

  @property
  def received(self) -> bytes:
    """The whole reply frame, or empty when nothing came back."""
    return self.header + self.payload


@dataclass
class Session:
  """Every exchange of one operation, in the order it happened.

  Attributes:
    operation: What the device was asked to do.
    exchanges: The frames it took, each with its reply.
    failure: What went wrong, or None when the operation finished.
  """

  operation: Operation
  exchanges: list[Exchange] = field(default_factory=list)
  failure: BaseException | None = None

  @property
  def sent(self) -> list[bytes]:
    """The frames that went out, in order."""
    return [exchange.sent for exchange in self.exchanges]


class LinkObserver(abc.ABC):
  """Told what a link does, in order.

  An operation brackets the frames it took: :meth:`operation_started`, then one
  :meth:`frame_sent` and at most one :meth:`frame_received` per exchange, then
  :meth:`operation_finished`. Frames sent outside any operation are reported on their own, with no
  bracket around them.
  """

  @abc.abstractmethod
  async def operation_started(self, operation: Operation) -> None:
    """Note that a device has begun an operation.

    Args:
      operation: What it was asked to do.
    """

  @abc.abstractmethod
  async def operation_finished(self, operation: Operation, failure: BaseException | None) -> None:
    """Note that a device has finished an operation.

    Args:
      operation: What it was asked to do.
      failure: What went wrong, or None when it finished.
    """

  @abc.abstractmethod
  async def frame_sent(self, frame: bytes) -> None:
    """Note a frame going out.

    Args:
      frame: The header followed by the payload, as it was written.
    """

  @abc.abstractmethod
  async def frame_received(self, header: bytes, payload: bytes) -> None:
    """Note a reply coming back.

    Args:
      header: The eleven reply header bytes.
      payload: The reply payload, as long as the header declared.
    """


class SessionRecorder(LinkObserver):
  """Collects each operation's frames, and keeps the ones the caller asks it to keep.

  This is the observer everything else is built on: a recorder holds the operation being carried
  out and the exchanges it has taken so far, and :meth:`session_finished` is where a subclass does
  something with a completed one. On its own it keeps every session in :attr:`sessions`.

  Attributes:
    sessions: The completed sessions, oldest first.
  """

  def __init__(self) -> None:
    self.sessions: list[Session] = []
    self._open: Session | None = None
    self._depth = 0

  async def operation_started(self, operation: Operation) -> None:
    """Open a session, unless one is already open.

    A nested operation is folded into the one around it, so an operation that brackets itself
    inside a larger one is reported once, as part of the larger one.

    Args:
      operation: What the device was asked to do.
    """
    self._depth += 1
    if self._depth == 1:
      self._open = Session(operation=operation)

  async def operation_finished(self, operation: Operation, failure: BaseException | None) -> None:
    """Close the session and hand it over.

    Args:
      operation: What the device was asked to do.
      failure: What went wrong, or None when it finished.
    """
    self._depth = max(self._depth - 1, 0)
    if self._depth or self._open is None:
      return
    session, self._open = self._open, None
    session.failure = failure
    await self.session_finished(session)

  async def frame_sent(self, frame: bytes) -> None:
    """Record a frame going out.

    Args:
      frame: The header followed by the payload.
    """
    if self._open is not None:
      self._open.exchanges.append(Exchange(sent=frame))

  async def frame_received(self, header: bytes, payload: bytes) -> None:
    """Record a reply against the frame that asked for it.

    Args:
      header: The eleven reply header bytes.
      payload: The reply payload.
    """
    if self._open is None or not self._open.exchanges:
      return
    exchange = self._open.exchanges[-1]
    exchange.header = header
    exchange.payload = payload

  async def session_finished(self, session: Session) -> None:
    """Do something with a completed session.

    Args:
      session: The operation and every frame it took.
    """
    self.sessions.append(session)


@asynccontextmanager
async def observed(observer: LinkObserver | None, operation: Operation) -> AsyncIterator[None]:
  """Bracket the frames of one operation.

  Nothing an observer raises reaches the caller: watching a link must not be able to break it, so a
  failure here is logged and the operation carries on.

  Args:
    observer: The observer to tell, or None to do nothing at all.
    operation: What the device is being asked to do.

  Yields:
    Nothing. The operation is open for the body of the block.
  """
  if observer is None:
    yield
    return
  await _quietly(observer.operation_started(operation))
  failure: BaseException | None = None
  try:
    yield
  except BaseException as error:
    failure = error
    raise
  finally:
    await _quietly(observer.operation_finished(operation, failure))


async def _quietly(awaitable) -> None:
  """Await something an observer is doing, swallowing whatever it raises.

  Args:
    awaitable: What the observer returned.
  """
  try:
    await awaitable
  except Exception:  # noqa: BLE001 -- an observer must never break the link it is watching.
    logger.exception("a link observer raised, and was ignored")
