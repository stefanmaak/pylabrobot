"""Communication with an instrument: transport selection, link lifecycle and byte-level I/O."""

from __future__ import annotations

from .connection import open_transport, transport_for
from .ftdi_transport import FtdiTransport, is_ftdi_port, serial_number
from .serial_transport import SerialTransport
from .transport import (
  BAUDRATE,
  DEFAULT_READ_TIMEOUT,
  DEFAULT_WRITE_TIMEOUT,
  Transport,
)

__all__ = [
  "BAUDRATE",
  "DEFAULT_READ_TIMEOUT",
  "DEFAULT_WRITE_TIMEOUT",
  "FtdiTransport",
  "SerialTransport",
  "Transport",
  "is_ftdi_port",
  "open_transport",
  "serial_number",
  "transport_for",
]
