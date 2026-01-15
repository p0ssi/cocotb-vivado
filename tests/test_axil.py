import cocotb_vivado
import pathlib

import cocotb
from cocotb_vivado import get_runner
from cocotb.triggers import Timer
from cocotb.clock import Clock

from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiLiteRam


@cocotb.test()
async def cocotb_axil_test(dut):

    clk = Clock(dut.clk, 200, units="ns")
    cocotb.start_soon(clk.start())

    dut.rst.value = 1
    await Timer(500, "ns")
    dut.rst.value = 0

    axil_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "axil"), dut.clk, dut.rst)
    axil_ram = AxiLiteRam(AxiLiteBus.from_prefix(dut, "axil"), dut.clk, dut.rst, size=2**16)

    data_in = list(range(16))

    await axil_master.write(0, data_in)

    data_out = []
    data_out = list((await axil_master.read(12, 4)).data) + data_out
    data_out = list((await axil_master.read(8, 4)).data) + data_out
    data_out = list((await axil_master.read(4, 4)).data) + data_out
    data_out = list((await axil_master.read(0, 4)).data) + data_out

    assert data_in == data_out


def test_axil():
    src_path = pathlib.Path(__file__).parent.absolute()
    toplevel = "test_axil"
    runner = get_runner("vivado")
    waves = False

    runner.build(
        sources=[src_path / "test_axil.v"],
        hdl_toplevel=toplevel,
        waves=waves,
        always=True  # always rebuild
    )

    runner.test(
        test_module=__name__,  # this module
        hdl_toplevel=toplevel,
        hdl_toplevel_lang="verilog",
        waves=waves,
    )

if __name__ == "__main__":
    test_axil()
