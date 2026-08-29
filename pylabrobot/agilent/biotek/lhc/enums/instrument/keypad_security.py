from __future__ import annotations

import enum


class KeypadSecurity(enum.IntEnum):
  """Whether the instrument's front-panel keypad accepts input.

  Locking the keypad prevents a bystander from interfering with a run in progress.
  """

  NONE = 0
  LOCKED = 1
