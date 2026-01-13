from cocotb_vivado import run
import subprocess
import os
import pathlib
import shutil

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Edge, Timer
from cocotb.binary import BinaryValue

import pytest


@cocotb.test()
async def cocotb_tb_test(dut):
    clk = Clock(dut.clk, 5, units="ns")
    cocotb.start_soon(clk.start())

    await Timer(10, "ns")

    for _ in range(10):
        await Edge(dut.out)
        cocotb.log.info(f"out={dut.out.value}")

    await Timer(100, "ns")

    for v in ["1", "0", "x", "z", "X", "Z", "0"]:
        dut.vec_in.setimmediatevalue(BinaryValue(v * 100))
        await Timer(10, "ns")
        vec_out = dut.vec_out.value
        cocotb.log.info(f"dut.vec_out {vec_out}")
        assert (v * 100).lower() == vec_out.binstr


@cocotb.test()
async def cocotb_tb_test_fail(dut):
    await Timer(10, "ns")
    assert 1 == 0


def run_tb(module="test_tb"):
    src_path = pathlib.Path(__file__).parent.absolute()

    shutil.rmtree("xsim.dir", ignore_errors=True)

    if not os.path.exists("xsim.dir/work.tb/xsimk.so"):
        subprocess.run(["xvlog", src_path / "tb.v"])
        subprocess.run(["xelab", "work.tb", "-dll"])

    run(module=module, xsim_design="xsim.dir/work.tb/xsimk.so", top_level_lang="verilog")


def test_tb():
    os.environ["TESTCASE"] = "cocotb_tb_test"
    run_tb()


@pytest.mark.xfail
def test_tb_fail():
    os.environ["TESTCASE"] = "cocotb_tb_test_fail"
    run_tb()


@pytest.mark.xfail
def test_tb_fail_init():
    os.environ["TESTCASE"] = "cocotb_tb_test"
    run_tb(module="no_exisitng")


if __name__ == "__main__":
    test_tb()
