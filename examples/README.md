# Examples

Runnable cocotb-vivado projects, each self-contained with its own DUT
sources, cocotb test, and a short README explaining what it
demonstrates.

| Example | Topic |
|---------|-------|
| [counter](counter/)       | Minimal "hello world": runner build + test of a synchronous counter |
| [parameters](parameters/) | Sweep a top-level Verilog parameter via `runner.build(parameters=...)` |
| [ip](ip/)                 | Instantiate a Vivado IP (`blk_mem_gen`) via `VivadoIp`, regenerated on first build |

All examples assume the Vivado environment is sourced (`xelab` /
`xvlog` / `xvhdl` on `PATH`, `LD_LIBRARY_PATH` set):

```bash
source /path/to/Vivado/<version>/settings64.sh
cd examples/<dir>
pytest -s
```

For development setup and architectural rules, see
[CONTRIBUTING.md](../CONTRIBUTING.md).
