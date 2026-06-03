"""Smoke test for the cocotb-vivado Python runner."""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.triggers import Timer

from cocotb_vivado.runner import get_runner


@cocotb.test()
async def simple_test(dut):
    dut.clk.value = 0
    await Timer(10, units="ns")
    assert dut.out.value == 0
    dut.clk.value = 1
    await Timer(10, units="ns")
    assert dut.out.value == 1


def test_simple():
    """Build tb.v with the Python runner and run the cocotb test."""
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "tb.v"]

    sim = os.getenv("SIM", "vivado")
    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel="tb",
        test_module="test_simple",
        hdl_toplevel_lang="verilog",
        testcase="simple_test",
    )


@pytest.mark.in_process_xsi
def test_simple_directlaunch():
    """Legacy ``cocotb_vivado.run()`` path, kept for regression coverage."""
    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    import cocotb_vivado  # noqa: PLC0415

    src_path = Path(__file__).resolve().parent
    shutil.rmtree("xsim.dir", ignore_errors=True)
    subprocess.run(["xvlog", str(src_path / "tb.v")], check=True)
    subprocess.run(["xelab", "work.tb", "-dll"], check=True)

    cocotb_vivado.run(
        module="test_simple",
        xsim_design="xsim.dir/work.tb/xsimk.so",
        top_level_lang="verilog",
    )


if __name__ == "__main__":
    test_simple()
