from __future__ import annotations

import enum


class ProductType(enum.IntEnum):
  """A model in the BioTek washer/dispenser family.

  Identifies which instrument a connection is expected to talk to. The model is declared rather
  than discovered: nothing in the wire protocol reports it.
  """

  UNDEFINED = 0
  EL406 = 1
  ELX405 = 2
  MICROFLO = 3
  MULTIFLO = 4
  MODEL_405_TS = 5
  MULTIFLO_FX = 6
  MODEL_50_TS = 7
