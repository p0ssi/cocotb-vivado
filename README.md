# cocotb-vivado
[![PyPI version](https://badge.fury.io/py/cocotb-vivado.svg)](https://pypi.org/project/cocotb-vivado/)

A limited Python/[cocotb](https://github.com/cocotb/cocotb/) interface to the [Xilinx Vivado Simulator](https://docs.xilinx.com/v/u/en-US/dh0010-vivado-simulation-hub) simulator. 
Based on [cocotb-stub-sim](https://github.com/fvutils/cocotb-stub-sim).

---

## 🚧 Project Status
**Proof of Concept** – expect limitations (see below).  

- Only top-level ports are accessible (simulator limitation).  
- Edge-triggers `Edge`, `RisingEdge`, `FallingEdge` only work on clocks generated in the testbench/python with cocotb.clock.Clock() driver." (simulator limitation, see below).
- Setting signal values is immediate (`setimmediatevalue` behavior).  
- Only **Verilog top-levels** are supported (VHDL support planned).  
- Direct access to the **XSI interface** is available.  

---

## Installation

```bash
pip install cocotb-vivado==0.0.3 (for VIVADO <= 2022.2)
pip install cocotb-vivado (for VIVADO >= 2023.1)
```

## Quickstart

```python
import subprocess

import cocotb_vivado
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def simple_test(dut):
    dut.clk.value = 0
    await Timer(10, units="ns")
    dut.clk.value = 1
    await Timer(10, units="ns")
    assert dut.out.value == 1

def test_simple():
    subprocess.run(["xvlog", "tb.v"])
    subprocess.run(["xelab", "work.tb", "-dll"])

    cocotb_vivado.run(module="test_simple", xsim_design="xsim.dir/work.tb/xsimk.so", top_level_lang="verilog")
```

See `testes/test_simple.py` for full example.

## Usage

See the `tests` folder for examples.

```bash
source ../Vivado/202X.X/settings64.sh
export LD_LIBRARY_PATH=$XILINX_VIVADO/lib/lnx64.o
pytest -s
```

Extra feature: One does not need to recompile the project when running/changing tests .

## Direct `XSI` interface

You can use `XSI` interface directly see `tests/test_xsi.py` for an example.

## Overcoming `XSI` limitations

`XSI` interface natively supports only `Timer` trigger.

To allow for using edge triggers under this limitation, cocotb-vivado  provides its custom trigger mechanism. When `cocotb_vivado` is imported, a global ClockScheduler singleton is created. This scheduler replaces cocotb’s standard implementations of `Clock`, `Edge`, `RisingEdge`, and `FallingEdge`.

The monkey‑patched Clock objects register themselves with the scheduler, which drives the associated signals and observes every resulting transition. On each clock‑driven edge, the scheduler evaluates all pending edge triggers and resumes any coroutines waiting on them. This polling‑on‑edge model gives deterministic behavior for multiple clocks while keeping the standard cocotb coroutine interface unchanged.

## cocotb extensions

In order to use cocotb extension like [cocotbext-axi](https://github.com/alexforencich/cocotbext-axi) one needs to use `Clock` driver for clocking their DUT.

## Full Vivado design simulation

In order order to simulate full design you need create design, `export_simulation` files compile, elaborate and run. See `tests/fw.tcl` and `tests/test_fw.tcl` for an example.

## Dump waveforms

You can dump `vcd` file with verilog syntax in your testbench:

```verilog
initial begin
    $dumpfile("test.vcd");
    $dumpvars(0);
end
```

### Acknowledgment

We'd like to thank our employer, [Dectris](https://dectris.com/) for supporting this work.
