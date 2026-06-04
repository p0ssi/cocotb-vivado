# ip

Demonstrates the three Vivado-managed source classes from
`cocotb_vivado.vivado` that slot into `runner.build(sources=[...])`:

```python
from cocotb_vivado.runner import get_runner
from cocotb_vivado.vivado import (
    VivadoIp,
    VivadoProject,
    VivadoExportedSim,
    discover_default_part,
)

runner = get_runner("vivado")

# .xci / .bd → VivadoIp (needs part_num). builder_tcl optionally
# produces the .xci on first run.
runner.build(
    sources=[
        "my_design.v",
        VivadoIp(
            "ip/my_ip/my_ip.xci",
            builder_tcl="ip/my_ip/regen.tcl",
            part_num="xczu7eg-ffvc1156-2-e",
        ),
    ],
    hdl_toplevel="my_top",
)

# .xpr → VivadoProject. builder_tcl optionally produces the .xpr on
# first run; part_num optionally retargets it in-memory for sim.
runner.build(
    sources=[
        VivadoProject(
            xpr_path="my_project.xpr",
            builder_tcl="build_project.tcl",
            part_num="xczu7eg-ffvc1156-2-e",
        ),
    ],
    hdl_toplevel="my_top",
)

# User-supplied TCL that drives its own launch_simulation extraction
runner.build(
    sources=[
        VivadoExportedSim(
            tcl_file="custom.tcl",
            result_dir="custom_sim",
        ),
    ],
    hdl_toplevel="my_top",
    hdl_library="xil_defaultlib",
)
```

Each source object self-orchestrates its Vivado batch call (with
mtime-based caching against the resulting `xsim/elaborate.sh` or
per-IP `xsim/README.txt`) and returns a `SimDirInfo` view that the
runner consumes — per-language `.prj` files for `xvlog -prj` /
`xvhdl -prj` plus the precompiled-library set (`-L` flags) and any
`<lib>.glbl` modules extracted from the sibling xelab `*.sh` script.
The runner itself never invokes the `vivado` binary directly — only
`xelab` / `xvlog` / `xvhdl`. Anything that runs `vivado` lives in
`cocotb_vivado.vivado`.

A working `VivadoProject` scenario is in `tests/test_fw.py`. It
points `VivadoProject` at `fw.xpr` (produced on first call by the
`builder_tcl` hook running `fw.tcl`), and the source object's own
`launch_simulation -scripts_only -absolute_path` invocation extracts
the per-language `.prj` files and `elaborate.sh` the runner picks
up.

## Run

```bash
source /path/to/Vivado/<version>/settings64.sh
cd tests
pytest -s test_fw.py     # full IP / BD via VivadoProject + builder_tcl
pytest -s test_axil.py   # RTL only, no Vivado source
```

(test_fw.py needs `cocotbext-axi` installed and Zynq UltraScale+
device support in your Vivado installation. The other examples in
`examples/counter/` and `examples/parameters/` have neither
requirement.)
