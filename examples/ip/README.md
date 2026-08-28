# ip

A runnable `VivadoIp` example: a Xilinx `blk_mem_gen` (1024×8 true
dual-port RAM) instantiated by the hand-written wrapper `bram_wrap.sv`,
which is the toplevel.

```
bram_wrap.sv                       toplevel wrapping the IP
ip/blk_mem_kilobyte/regen.tcl      recipe that generates the .xci
test_ip.py                         the cocotb test + runner build
```

The `.xci` is **not committed** — `VivadoIp`'s `builder_tcl` hook runs
`regen.tcl` on the first build to produce it for whatever Vivado you
have, so the example is version-agnostic.

## Run

```bash
source /path/to/Vivado/<version>/settings64.sh
pytest -s examples/ip/test_ip.py
```

The build wires the IP in with a single `VivadoIp` entry in
`sources=[...]`; the runner never calls `vivado` directly — the source
object regenerates the IP and hands back the `.prj` / library set that
`xvlog` / `xelab` consume.

See the [top-level README](../../README.md#vivado-managed-sources-ip--bd--xpr)
for the full source-class table (`VivadoIp` / `VivadoBd` /
`VivadoProject` / `VivadoExportedSim`) and the `tests/` directory for
BD and project scenarios.
