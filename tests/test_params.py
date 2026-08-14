"""Verify ``runner.build(parameters=...)`` forwards values to xelab via ``-generic_top``.

Also probes the error path: an unknown parameter name should make xelab
fail with ``[XSIM 43-3281]``, which the runner surfaces as
``SystemExit``.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.triggers import Timer

from cocotb_vivado.runner import get_runner


@cocotb.test()
async def cocotb_param_test(dut):
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
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "tb_params.v"]

    sim = os.getenv("SIM", "vivado")
    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel="tb_params",
        always=True,
        timescale=("1ns", "1ps"),
        parameters=parameters,
    )
    runner.test(
        hdl_toplevel="tb_params",
        test_module="test_params",
        hdl_toplevel_lang="verilog",
        testcase="cocotb_param_test",
    )


def test_params_default():
    os.environ["EXPECTED_WIDTH"] = "8"
    os.environ["EXPECTED_DEPTH"] = "4"
    _run(parameters={})


def test_params_override():
    os.environ["EXPECTED_WIDTH"] = "16"
    os.environ["EXPECTED_DEPTH"] = "7"
    _run(parameters={"WIDTH": 16, "DEPTH": 7})


def test_params_unknown():
    os.environ["EXPECTED_WIDTH"] = "8"
    os.environ["EXPECTED_DEPTH"] = "4"
    with pytest.raises(SystemExit):
        _run(parameters={"NOT_A_REAL_PARAM": 1234})


if __name__ == "__main__":
    test_params_default()
    test_params_override()
    test_params_unknown()
