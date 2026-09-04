"""Sweep a top-level Verilog parameter from the Python runner.

Demonstrates ``runner.build(parameters=...)`` forwarding values to xelab
via ``-generic_top``. The cocotb test reads the resulting bit width from
the elaborated design.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.triggers import Timer

from cocotb_vivado.runner import get_runner


@cocotb.test()
async def check_width(dut):
    expected = int(os.environ["EXPECTED_WIDTH"])
    await Timer(1, "ns")
    assert len(dut.vec_out) == expected, (
        f"expected vec_out width {expected}, got {len(dut.vec_out)}"
    )


def _run(width):
    os.environ["EXPECTED_WIDTH"] = str(width)
    here = Path(__file__).resolve().parent
    build_dir = here / "sim_build"
    runner = get_runner(os.getenv("SIM", "vivado"))
    runner.build(
        sources=[here / "params_dut.v"],
        hdl_toplevel="params_dut",
        always=False,
        parameters={"WIDTH": width},
        timescale=("1ns", "1ps"),
        build_dir=str(build_dir),
    )
    runner.test(
        hdl_toplevel="params_dut",
        test_module="test_parameters",
        hdl_toplevel_lang="verilog",
        testcase="check_width",
        build_dir=str(build_dir),
    )


@pytest.mark.parametrize("width", [8, 16, 32, 64])
def test_width_sweep(width):
    _run(width)


if __name__ == "__main__":
    for w in (8, 16, 32, 64):
        _run(w)
