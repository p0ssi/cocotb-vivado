"""
Tests that the python runner correctly forwards top-level parameters to xelab
via the ``parameters=...`` kwarg of ``runner.build()``.

Also probes the behavior when an unknown parameter is injected.
"""
import os
from pathlib import Path

import cocotb_vivado
from cocotb_vivado import get_runner

import cocotb
from cocotb.triggers import Timer

import pytest


@cocotb.test()
async def cocotb_param_test(dut):
    """Verify parameter values took effect by inspecting signal widths."""
    expected_width = int(os.environ["EXPECTED_WIDTH"])
    expected_depth = int(os.environ["EXPECTED_DEPTH"])

    await Timer(1, "ns")

    assert len(dut.vec_out) == expected_width, (
        f"expected vec_out width {expected_width}, got {len(dut.vec_out)}"
    )
    assert len(dut.depth_out) == expected_depth, (
        f"expected depth_out width {expected_depth}, got {len(dut.depth_out)}"
    )


def _run(parameters):
    """Build tb_params with the given parameters dict and run the cocotb test."""
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "tb_params.v"]

    sim = os.getenv("SIM", "vivado")
    toplevel = "tb_params"

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=toplevel,
        always=True,
        timescale=("1ns", "1ps"),
        parameters=parameters,
        waves=False,
    )
    runner.test(
        hdl_toplevel=toplevel,
        test_module="test_params",
        hdl_toplevel_lang="verilog",
        testcase="cocotb_param_test",
        waves=False,
    )


def test_params_default():
    """No overrides: defaults (WIDTH=8, DEPTH=4) must apply."""
    os.environ["EXPECTED_WIDTH"] = "8"
    os.environ["EXPECTED_DEPTH"] = "4"
    _run(parameters={})


def test_params_override():
    """Override both parameters and verify they take effect."""
    os.environ["EXPECTED_WIDTH"] = "16"
    os.environ["EXPECTED_DEPTH"] = "7"
    _run(parameters={"WIDTH": 16, "DEPTH": 7})


def test_params_unknown():
    """
    Inject a parameter name that does not exist in the verilog top.
    Documents whether xelab/the runner surface this as a proper error.
    """
    os.environ["EXPECTED_WIDTH"] = "8"
    os.environ["EXPECTED_DEPTH"] = "4"
    with pytest.raises(SystemExit):
        _run(parameters={"NOT_A_REAL_PARAM": 1234})


if __name__ == "__main__":
    test_params_default()
    test_params_override()
    test_params_unknown()
