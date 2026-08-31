.. currentmodule:: pylabrobot.agilent

pylabrobot.agilent package
==========================

BenchCel 4R
-----------

.. currentmodule:: pylabrobot.agilent.benchcel

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    BenchCel4R
    BenchCelLabwareSettings
    PlateNotchSettings


BioTek washers and dispensers
-----------------------------

One class per model. Each exposes the capability objects its fitted hardware supports.

.. currentmodule:: pylabrobot.agilent.biotek.lhc

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    EL406
    MultiFlo
    MultiFloFX
    Washer405TS
    Protocol
    read
    write

.. currentmodule:: pylabrobot.agilent.biotek.lhc.devices.components

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    PlateWasher
    SyringeDispenser
    PeristalticDispenser

.. currentmodule:: pylabrobot.agilent.biotek.lhc.devices

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    InstrumentSettings
    SettingsComparison

.. currentmodule:: pylabrobot.agilent.biotek.lhc.protocols.validation

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    ValidationReport
    StepReport
    Rejection

.. currentmodule:: pylabrobot.agilent.biotek.lhc.error_handling

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    BiotekError
    LinkError
    RejectedError


BioTek Cytation
---------------

.. currentmodule:: pylabrobot.agilent.biotek.cytation

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    Cytation1
    Cytation5
    CytationImagingConfig


BioTek Synergy H1
------------------

.. currentmodule:: pylabrobot.agilent.biotek.synergy

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    SynergyH1


VSpin
-----

.. currentmodule:: pylabrobot.agilent.vspin

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    VSpin
    Access2
    Access2Driver
