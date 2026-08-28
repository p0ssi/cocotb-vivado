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
- `tests/test_axil.py` and `tests/test_fw.py` are on the new runner.
  test_axil is pure RTL; test_fw uses `VivadoProject` (below).
- `tests/test_xsi.py` is still skip-gated behind
  `COCOTB_VIVADO_TEST_DIRECT=1` — it is a low-level XSI ctypes smoke
  test rather than a runner-based simulation.

## Vivado-managed sources (IP / BD / XPR)

`.xci`, `.bd`, and `.xpr` files are passed to the runner via
**source objects** from `cocotb_vivado.vivado`:

A source object sits in the same `sources=` list as plain HDL. An IP
alongside the RTL that instantiates it (`tests/test_bram.py`):

```python
from pathlib import Path

from cocotb_vivado.runner import get_runner
from cocotb_vivado.vivado import VivadoIp

here = Path(__file__).resolve().parent
runner = get_runner("vivado")
runner.build(
    sources=[
        VivadoIp(
            "ip/blk_mem_kilobyte/blk_mem_kilobyte.xci",
            builder_tcl=here / "ip" / "blk_mem_kilobyte" / "regen.tcl",
            part_num="xczu7eg-ffvc1156-2-e",
        ),
        here / "bram_wrap.sv",
    ],
    hdl_toplevel="bram_wrap",
)
```

A relative `.xci` / `.bd` path resolves under the *build directory* (where
`builder_tcl` deposits it); `builder_tcl` itself resolves against the
current working directory, so pass it absolute.

A whole project as the design under test (`tests/test_fw.py`):

```python
from cocotb_vivado.vivado import VivadoProject

runner.build(
    sources=[VivadoProject(xpr_path="fw/fw.xpr", builder_tcl="fw.tcl")],
    hdl_toplevel="my_top",
)
```

**One design-defining source per build.** `hdl_library` is a single
setting for the whole build, and `VivadoBd` / `VivadoProject` /
`VivadoExportedSim` each extract into `xil_defaultlib` — combining two of
them merges two independently generated structural HDL sets into one
library. Use at most one, plus any number of `VivadoIp` and plain HDL
sources.

Each source class self-orchestrates:

- **`VivadoIp(*xci_or_bd_paths, part_num=...)`** runs
  `set_part; add_files -norecurse; export_ip_user_files` when an IP
  source is newer than its prior `xsim/README.txt`. `part_num` is
  required (falls back to `COCOTB_DEFAULT_PART_NUM` env);
  `discover_default_part()` is an opt-in helper that queries Vivado
  once and caches the answer.
- **`VivadoProject(xpr_path, builder_tcl=..., part_num=...)`** runs
  `open_project; launch_simulation -scripts_only -absolute_path` with
  mtime caching against the resulting `xsim/elaborate.sh`. Output
  lands in Vivado's default `{xpr_stem}.sim/sim_1/behav/xsim/`. The
  project carries its own part; `part_num` is only needed to
  *retarget* in-memory for simulation. The optional `builder_tcl`
  produces the `.xpr` on first run.
- **`VivadoExportedSim(tcl_file, result_dir, result_file=...)`** is
  the catch-all for TCL scripts that drive their own
  `launch_simulation -scripts_only` extraction.

## Edge triggers now see same-timestep deposits

The value-change manager behind edge / read-write / read-only callbacks
changed one observable behavior versus the older polling scheduler: a
signal written in the *same* timestep as a clock edge is now visible to
that edge — as in a real simulator (cocotb applies coroutine deposits
before the simulator evaluates the timestep). The old scheduler sampled
the *stale* value.

Concretely, a testbench that releases reset *exactly* on a clock edge
now counts one cycle later than before. If a test that used to pass
starts counting one cycle early, that is why: the old behavior was
wrong. Release reset *between* edges, or expect the extra cycle —
`examples/counter` was corrected this way (verified against nvc with
stock cocotb).

The runner consumes each source's `xsim/` directory uniformly:
discovers per-language `.prj` files by content sniff and parses the
`xelab` invocation in the sibling `*.sh` script for the precompiled-
library set (`-L` flags) and any `<lib>.glbl` extras. Plain HDL
sources flow through `xvlog` / `xvhdl` directly. Pure-RTL builds
without any `VivadoSource` instance never touch the `vivado` binary
— `xelab` / `xvlog` / `xvhdl` are the only external programs invoked.

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
