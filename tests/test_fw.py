from cocotb_vivado import get_runner, execute_tcl
import pathlib

import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock

from cocotbext.axi import AxiLiteBus, AxiLiteMaster
from cocotbext.axi import AxiStreamSink, AxiStreamSource, AxiStreamBus


async def reset(signal, timer):
    signal.value = 1
    await timer
    signal.value = 0


@cocotb.test()
async def cocotb_fw_test(dut):
    AXIS_FIFO_BASEADDR = 0x1000

    clk = Clock(dut.aclk, 200, units="ns")
    cocotb.start_soon(clk.start())

    cocotb.start_soon(reset(dut.areset, Timer(520, "ns")))

    axil_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.aclk, dut.areset)
    axis_rx = AxiStreamSource(AxiStreamBus.from_prefix(dut, "AXIS_RX"), dut.aclk, dut.areset)
    axis_tx = AxiStreamSink(AxiStreamBus.from_prefix(dut, "AXIS_TX"), dut.aclk, dut.areset)

    data_in = list(range(32))
    await axil_master.write(0x10, data_in)
    data_out = list((await axil_master.read(0x10, 32)).data)

    print(data_in)
    print(data_out)

    assert data_in == data_out

    #

    rx_data_send = []
    for i in range(4):
        d = list(range((i + 1) * 4))
        rx_data_send += d
        await axis_rx.write(d)
        await axis_rx.wait()

    # rx_data = range(10)
    rx_size = list((await axil_master.read(AXIS_FIFO_BASEADDR + 0x1C, 4)).data)
    assert rx_size == [10, 0, 0, 0]

    rx_data = []
    for _ in range(10):
        rx_data += list((await axil_master.read(AXIS_FIFO_BASEADDR + 0x20, 4)).data)

    assert rx_data == rx_data_send

    #

    for i in range(8):
        await axil_master.write(AXIS_FIFO_BASEADDR + 0x10, list(range(i * 4, i * 4 + 4)))
        await axil_master.wait()

    await axil_master.write(AXIS_FIFO_BASEADDR + 0x14, [0x20, 0, 0, 0])

    # tx_size = list((await axil_master.read(AXIS_FIFO_BASEADDR + 0xC, 4)).data)
    # print("tx_size", tx_size)

    tx_data = (await axis_tx.recv()).tdata
    assert bytearray(range(8 * 4)) == tx_data

    dut.areset.value = 0

def test_fw():
    src_path = pathlib.Path(__file__).parent.absolute()
    tcl_path = src_path / "fw.tcl"
    xpr_path = src_path / "fw" / "fw.xpr"
    toplevel = "fw_wrapper"
    runner = get_runner("vivado")
    waves = False

    # run tcl script to generate project file when generated xpr is outdated or missing.
    execute_tcl(tcl_path, output=xpr_path)

    runner.build(
        sources=[xpr_path],
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
    test_fw()
