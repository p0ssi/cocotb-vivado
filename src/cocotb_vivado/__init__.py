"""cocotb-vivado package init.

Importing this package has two global side effects:

1. ``cocotb.simulator`` in ``sys.modules`` is replaced with the
   in-process XSI stub. This is how the runner injects a GPI shim
   that cocotb can talk to.
2. ``cocotb.clock.Clock`` and the ``cocotb.triggers.{Edge, RisingEdge,
   FallingEdge}`` classes are replaced with scheduler-driven polling
   equivalents from :mod:`cocotb_vivado.clock_scheduler`. The stub
   rejects ``register_value_change_callback``, so the real cocotb edge
   triggers cannot work; the polling stand-ins fill that gap until the
   stub layer learns proper value-change callbacks.

Consequence — **import order matters**. Always import ``cocotb_vivado``
(or any ``cocotb_vivado.*`` submodule) before ``cocotb``. Importing
``cocotb`` first caches the real C-extension simulator and the patch
silently becomes a no-op:

.. code-block:: python

    # Correct
    import cocotb_vivado
    from cocotb_vivado.runner import get_runner
    import cocotb

    # Broken — cocotb caches the real simulator before our patch lands
    import cocotb
    import cocotb_vivado

For the trigger patches to win, reference the trigger classes via the
module path inside your test:

.. code-block:: python

    @cocotb.test()
    async def t(dut):
        await cocotb.triggers.RisingEdge(dut.clk)  # uses the patched class

``from cocotb.triggers import RisingEdge`` followed by ``RisingEdge(...)``
binds the *original* class regardless of these patches, because Python
resolves the name at import time.

Both side effects are tracked for removal once the stub layer ships
proper value-change callback support, at which point the trigger
patches go away and cocotb's native edge triggers Just Work.
"""

import importlib
import os
import sys

# Replace cocotb.simulator BEFORE cocotb is imported so the GPI shim is
# in place when cocotb wires up its callbacks.
sys.modules["cocotb.simulator"] = importlib.import_module(
    "cocotb_vivado.stub.simulator"
)

import cocotb  # noqa: E402
import cocotb.clock  # noqa: E402
import cocotb.triggers  # noqa: E402

from . import clock_scheduler  # noqa: E402
from .stub.mgr import Mgr  # noqa: E402

# Patch cocotb's Clock and edge-trigger classes with scheduler-driven
# stand-ins. The XSI stub does not support value-change callbacks, so
# cocotb's native RisingEdge/FallingEdge/Edge cannot fire; the polling
# implementations from clock_scheduler bridge the gap.
cocotb.clock.Clock = clock_scheduler.ScheduledClock
cocotb.triggers.RisingEdge = clock_scheduler.RisingEdge
cocotb.triggers.FallingEdge = clock_scheduler.FallingEdge
cocotb.triggers.Edge = clock_scheduler.Edge


def run(module, xsim_design, top_level_lang):
    """Legacy direct-launch entry; superseded by ``cocotb_vivado.runner.Vivado``."""
    if top_level_lang != "verilog":
        raise Exception("Only verilog supported as top level languge")

    os.environ["MODULE"] = module

    mgr = Mgr.init(xsim_design)

    cocotb._initialise_testbench([])

    mgr.run()

    mgr.close()

    if cocotb.regression_manager.failures:
        sys.exit(1)
