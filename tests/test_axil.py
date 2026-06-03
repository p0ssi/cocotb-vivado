import os
import pathlib
import shutil
import subprocess

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiLiteRam

import cocotb_vivado
import cocotb_vivado.mock_triggers


@cocotb.test()
async def cocotb_axil_test(dut):

    clk = Clock(dut.clk, 200, units="ns")
    cocotb.start_soon(clk.start())

    dut.rst.value = 1
    await Timer(500, "ns")
    dut.rst.value = 0

    axil_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "axil"), dut.clk, dut.rst)
    AxiLiteRam(AxiLiteBus.from_prefix(dut, "axil"), dut.clk, dut.rst, size=2**16)

    data_in = list(range(16))

    await axil_master.write(0, data_in)

    data_out = []
    data_out = list((await axil_master.read(12, 4)).data) + data_out
    data_out = list((await axil_master.read(8, 4)).data) + data_out
    data_out = list((await axil_master.read(4, 4)).data) + data_out
    data_out = list((await axil_master.read(0, 4)).data) + data_out

    assert data_in == data_out


@pytest.mark.in_process_xsi
def test_axil():
    src_path = pathlib.Path(__file__).parent.absolute()

    shutil.rmtree("xsim.dir", ignore_errors=True)

    if not os.path.exists("xsim.dir/work.test_axil/xsimk.so"):
        subprocess.run(["xvlog", src_path / "test_axil.v"])
        subprocess.run(["xelab", "work.test_axil", "-dll"])

    cocotb_vivado.run(
        module="test_axil",
        xsim_design="xsim.dir/work.test_axil/xsimk.so",
        top_level_lang="verilog",
    )


if __name__ == "__main__":
    test_axil()
