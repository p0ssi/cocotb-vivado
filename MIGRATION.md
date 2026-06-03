# Migration guide

This document describes how to move existing cocotb-vivado tests onto
the new Python runner API.

## From the legacy `cocotb_vivado.run()` direct-launch path

Existing tests build the simulator binary themselves by spawning
`xvlog` / `xelab` as subprocesses, then call `cocotb_vivado.run()` to
load the resulting `.so` and execute the cocotb regression:

```python
import cocotb_vivado
import subprocess
import shutil
import pathlib

def test_simple():
    src_path = pathlib.Path(__file__).parent.absolute()
    shutil.rmtree("xsim.dir", ignore_errors=True)
    if not os.path.exists("xsim.dir/work.tb/xsimk.so"):
        subprocess.run(["xvlog", src_path / "tb.v"])
        subprocess.run(["xelab", "work.tb", "-dll"])
    cocotb_vivado.run(
        module="test_simple",
        xsim_design="xsim.dir/work.tb/xsimk.so",
        top_level_lang="verilog",
    )
```

The new path moves the build/elab orchestration into a
`cocotb.runner.Simulator` subclass:

```python
import os
from pathlib import Path
from cocotb_vivado.runner import get_runner

def test_simple():
    proj_path = Path(__file__).resolve().parent
    runner = get_runner(os.getenv("SIM", "vivado"))
    runner.build(
        sources=[proj_path / "tb.v"],
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

Both paths coexist for now. The legacy `cocotb_vivado.run()` function
remains importable; the new runner is the recommended path going
forward. The existing in-tree tests have been updated as follows:

- `tests/test_simple.py` and `tests/test_tb.py` now use the new runner
  by default. Their legacy variants are kept under
  `@pytest.mark.skipif(... COCOTB_VIVADO_TEST_DIRECT=1 ...)` for
  regression coverage.
- `tests/test_axil.py`, `tests/test_fw.py`, and `tests/test_xsi.py`
  are skip-gated at the module level behind the same env var. They
  will move to the new runner alongside IP / BD / XPR support.

## Environment

Before running tests:

- `xelab` / `xvlog` / `xvhdl` must be on `PATH` (source your Vivado
  `settings64.sh`).
- `LD_LIBRARY_PATH` must be set so the in-process XSI shared library
  can be loaded by the test subprocess. If unset, the runner falls
  back to constructing one from `XILINX_VIVADO`.

## Waveform output

The new runner takes an explicit `wave_format` kwarg on
`runner.build()` / `runner.test()`:

```python
runner.build(..., wave_format="vcd")      # Verilog $dumpfile/$dumpvars
runner.build(..., wave_format="fst")      # VCD then post-processed by vcd2fst
runner.build(..., wave_format="wdb")      # Vivado native
runner.build(...)                          # default: no waves
```

All three formats land at `{build_dir}/{hdl_toplevel}.{ext}` for
symmetry. `wave_format="fst"` auto-downgrades to `"vcd"` with a warning
when `vcd2fst` is not on `PATH`.

## Tested Vivado versions

The runner is tested against Vivado **2023.1** as the minimum supported
version. Newer Vivado versions are expected to work but may have
version-specific quirks; see the project README for currently verified
versions.

## Platform support

Linux only. cocotb-vivado loads XSI shared libraries
(`libxv_simulator_kernel.so`, `xsimk.so`) via ctypes; the XSI
interface is Linux-specific.
