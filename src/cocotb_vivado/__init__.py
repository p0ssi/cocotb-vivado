import sys
import importlib
import traceback

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

# monkey-patch get_runner()
import cocotb.runner
from .vivado_runner import get_runner
cocotb.runner.get_runner = get_runner
