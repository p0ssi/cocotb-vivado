import sys
import importlib
import traceback
import os

sys.modules["cocotb.simulator"] = importlib.import_module("cocotb_vivado.stub.simulator")

import cocotb

# monkey-patch the clock & trigger layer
import cocotb.clock
import cocotb.triggers
from .clock_scheduler import ScheduledClock, RisingEdge, FallingEdge, Edge
cocotb.clock.Clock = ScheduledClock
cocotb.triggers.RisingEdge = clock_scheduler.RisingEdge
cocotb.triggers.FallingEdge = clock_scheduler.FallingEdge
cocotb.triggers.Edge = clock_scheduler.Edge

from .stub.mgr import Mgr


def run(module, xsim_design, top_level_lang):
    if top_level_lang != "verilog":
        raise Exception("Only verilog supported as top level languge")

    os.environ["MODULE"] = module

    mgr = Mgr.init(xsim_design)

    cocotb._initialise_testbench([])

    mgr.run()

    mgr.close()

    if cocotb.regression_manager.failures:
        exit(1)
