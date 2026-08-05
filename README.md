# cocotb-vivado

[![PyPI version](https://badge.fury.io/py/cocotb-vivado.svg)](https://pypi.org/project/cocotb-vivado/)
[![lint](https://github.com/themperek/cocotb-vivado/actions/workflows/lint.yml/badge.svg)](https://github.com/themperek/cocotb-vivado/actions/workflows/lint.yml)

A Python/[cocotb](https://github.com/cocotb/cocotb/) interface to the
[Xilinx Vivado Simulator](https://docs.xilinx.com/v/u/en-US/dh0010-vivado-simulation-hub).

Based on [cocotb-stub-sim](https://github.com/fvutils/cocotb-stub-sim).
The Python runner and the value-change manager are derived from
[vicoco](https://github.com/kiran-vuksanaj/vicoco) by Kiran Vuksanaj.

---

## Project status

**Active development.** The Python runner experience is being rebuilt.
See [CHANGELOG.md](CHANGELOG.md) for what's landed and
[MIGRATION.md](MIGRATION.md) for breaking changes.

Known limitations:

- Only top-level ports are accessible (XSI limitation).
- Edge triggers (`Edge`, `RisingEdge`, `FallingEdge`) only fire on
  clocks driven by `cocotb.clock.Clock()` in the testbench. Native
  value-change callbacks are not supported by the XSI stub today;
  the scheduler-driven stand-ins from
  `cocotb_vivado.clock_scheduler` cover only Python-driven signals.
- Setting signal values is immediate (`setimmediatevalue` behavior).
- VHDL top-level support is in progress; today's release runs Verilog
  tops cleanly and accepts VHDL sources.
- Direct access to the **XSI interface** via `cocotb_vivado.xsi` is
  available for low-level tooling.

## Platform support

**Linux only.** cocotb-vivado loads XSI shared libraries via ctypes;
the XSI interface is Linux-specific.

## Tested Vivado versions

- Vivado **2023.1** — minimum supported.
- Newer versions are expected to work but verify locally.

## Installation

```bash
pip install cocotb-vivado
```

## Quickstart

```python
from pathlib import Path

import cocotb
from cocotb.triggers import Timer

from cocotb_vivado.runner import get_runner


@cocotb.test()
async def simple_test(dut):
    dut.clk.value = 0
    await Timer(10, units="ns")
    dut.clk.value = 1
    await Timer(10, units="ns")
    assert dut.out.value == 1


def test_simple():
    runner = get_runner("vivado")
    runner.build(
        sources=[Path(__file__).parent / "tb.v"],
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
```

See [`examples/`](examples/) for runnable projects and the `tests/`
directory for more scenarios.

Before running:

```bash
source /path/to/Vivado/<version>/settings64.sh
pytest -s tests/
```

`xelab` / `xvlog` / `xvhdl` must be on `PATH` and `LD_LIBRARY_PATH`
must be set (or `XILINX_VIVADO` set as a courtesy fallback so the
runner can synthesize one for the test subprocess).

## Import order caveat

Importing `cocotb_vivado` has two global side effects:

1. It replaces `cocotb.simulator` in `sys.modules` with the in-process
   XSI stub.
2. It replaces `cocotb.clock.Clock` and the
   `cocotb.triggers.{RisingEdge, FallingEdge, Edge}` classes with
   scheduler-driven polling stand-ins from
   `cocotb_vivado.clock_scheduler`. The XSI stub does not support
   value-change callbacks, so cocotb's native edge triggers cannot fire
   — these stand-ins bridge the gap. A global `ClockScheduler`
   singleton owns this state: patched `Clock` objects register
   themselves with the scheduler, which drives the signals and
   evaluates pending edge triggers on every clock-driven transition.

Consequence: **always import `cocotb_vivado` (or any `cocotb_vivado.*`
submodule) before `cocotb`**.

```python
# Correct
import cocotb_vivado
from cocotb_vivado.runner import get_runner

import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock
```

```python
# Broken — cocotb caches the real simulator before our patch lands
import cocotb
import cocotb_vivado
```

Reference the patched triggers via the module path inside your test so
the patch wins:

```python
@cocotb.test()
async def t(dut):
    await cocotb.triggers.RisingEdge(dut.clk)   # uses the patched class
```

`from cocotb.triggers import RisingEdge` followed by `RisingEdge(...)`
binds the *original* class regardless of the patches, because Python
resolves the name at import time.

## Waveform output

The `wave_format` kwarg on `runner.build()` / `runner.test()` selects
the dump format:

```python
runner.build(..., wave_format="vcd")      # Verilog $dumpfile/$dumpvars
runner.build(..., wave_format="fst")      # VCD post-processed by vcd2fst
runner.build(..., wave_format="wdb")      # Vivado native, viewable in xsim --gui
runner.build(...)                          # default: no waves
```

All formats land in `{build_dir}/{hdl_toplevel}.{ext}` for symmetry.

## cocotb extensions

Extensions like [cocotbext-axi](https://github.com/alexforencich/cocotbext-axi)
work as long as the DUT is clocked by a Python-driven `Clock` — see
the Import order caveat for why. AXI bus accesses are routed through
the cocotb scheduler the extension expects.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgment

We'd like to thank our employer, [Dectris](https://dectris.com/) for
supporting this work.
