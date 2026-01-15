import pathlib

import cocotb_vivado
from cocotb_vivado import get_runner
import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def simple_test(dut):
    dut.clk.value = 0
    await Timer(10, units="ns")
    assert dut.out.value == 0
    dut.clk.value = 1
    await Timer(10, units="ns")
    assert dut.out.value == 1


def test_simple():
    src_path = pathlib.Path(__file__).parent.absolute()

    toplevel = "tb"
    waves = False
    runner = get_runner("vivado")

    runner.build(
        sources=[src_path / "tb.v"],
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
    test_simple()
