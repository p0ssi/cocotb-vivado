"""Exercise the value-change manager's edge triggers on a plain RTL DUT.

`edge_dut.tog` flips on every rising `clk` edge, so RisingEdge and
FallingEdge on both `clk` and `tog` fire on something real. If the
manager's callback dispatch were broken these awaits would hang and the
test would time out — so this is a direct check that value-change
callbacks fire (and, with the inline re-registration below, that the
manager's snapshot/fire/remove dispatch is iteration-safe).
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from cocotb_vivado.runner import get_runner


@cocotb.test()
async def clock_edges_advance(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start(start_high=False))

    # tog toggles once per rising clk edge; confirm RisingEdge(clk) fires
    # repeatedly (re-registered inline each iteration) and the DUT
    # advances in lockstep.
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")  # let the non-blocking assignment settle
    prev = int(dut.tog.value)
    toggles = 0
    for _ in range(6):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        cur = int(dut.tog.value)
        toggles += int(cur != prev)
        prev = cur
    assert toggles == 6, f"tog should flip on every rising edge; got {toggles}"


@cocotb.test()
async def edges_on_a_data_signal(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start(start_high=False))

    # tog: 0 -> 1 -> 0 -> 1 ... on successive rising clk edges. Both a
    # falling and a rising edge of the data signal must fire.
    await FallingEdge(dut.tog)
    assert int(dut.tog.value) == 0
    await RisingEdge(dut.tog)
    assert int(dut.tog.value) == 1


def test_value_change():
    here = Path(__file__).resolve().parent
    runner = get_runner(os.getenv("SIM", "vivado"))
    runner.build(
        sources=[here / "edge_dut.v"],
        hdl_toplevel="edge_dut",
        always=True,
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel="edge_dut",
        test_module="test_value_change",
        hdl_toplevel_lang="verilog",
    )


if __name__ == "__main__":
    test_value_change()
