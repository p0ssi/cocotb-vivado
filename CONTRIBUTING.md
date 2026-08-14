# Contributing to cocotb-vivado

## Development environment

cocotb-vivado is **Linux-only**. The package loads XSI shared libraries
(`libxv_simulator_kernel.so`, `xsimk.so`) via ctypes; the XSI interface
is Linux-specific and there are no plans to support Windows or macOS.

You need:

- Python 3.10 or newer.
- A Linux install of Xilinx Vivado. Vivado 2023.1 is the minimum tested
  version; newer ones are expected to work but verify locally.
- `vcd2fst` from gtkwave (optional, only needed if you select
  `wave_format="fst"`).

Set up:

```bash
# Source your Vivado environment so xelab/xvlog/xvhdl/vivado are on PATH.
# Note settings64.sh does NOT export LD_LIBRARY_PATH on every install --
# export it yourself so the XSI shared libraries can be dlopened:
source /path/to/Vivado/<version>/settings64.sh
export LD_LIBRARY_PATH=$XILINX_VIVADO/lib/lnx64.o

# Editable install of the project + test and dev dependencies
pip install -e ".[dev]"

# (Optional) install pre-commit hooks so the linters run on every commit
pre-commit install
```

## Running tests

```bash
cd tests
pytest -s test_simple.py        # one test
pytest -s                       # the whole suite
```

Tests spawn `python -m cocotb_vivado` as a subprocess that loads XSI in
process. The Vivado binaries must be reachable on `PATH`. For those tests
`LD_LIBRARY_PATH` need not be set in your shell -- the runner exports it
for the subprocess, synthesizing it from `XILINX_VIVADO` when absent.

`tests/test_xsi.py` is the exception: it dlopens `xsimk.so` *in the pytest
process* via ctypes, so it needs `LD_LIBRARY_PATH` exported **before**
Python starts. Setting it from inside the process does not work -- the
dynamic loader captures its search path at exec time. The test skips
itself with an explanatory message when the XSI kernel library is not
loadable, so a missing `LD_LIBRARY_PATH` is a skip, not a failure.

`tests/test_fw.py` still exercises the legacy `cocotb_vivado.run()` path
and is skipped by default pending its migration to the runner; set
`COCOTB_VIVADO_TEST_DIRECT=1` to run it. Everything else runs
unconditionally.

## Linting and type checking

```bash
ruff check .
ruff format --check .
mypy src/
```

`pre-commit run --all-files` runs all of the above plus the basic
whitespace / line-ending hooks.

## Architectural rule

**`cocotb_vivado.runner` invokes only the XSim binaries** (`xelab` /
`xvlog` / `xvhdl`). The full `vivado` tool is not invoked from this
module — that surface (TCL execution, IP regeneration, project export,
part discovery) belongs to a separate module introduced in a follow-up
PR alongside support for Vivado-managed sources (`.xci`, `.bd`, `.xpr`).

## Why a separate package, not upstream cocotb

Reasonable question to ask once. The short answer:

- **Vivado XSim does not expose VPI or VHPI.** Every cocotb upstream
  simulator backend (Icarus, Verilator, Questa, GHDL, Riviera,
  Xcelium, NVC) talks to its simulator through VPI / VHPI / FLI via a
  cocotb-maintained C shim. Vivado ships only XSI — a low-level
  kernel API with no value-change callback registration. `xelab` has
  no `-loadvpi` equivalent. It's an architectural mismatch, not a
  missing-feature gap.
- **The XSI workarounds don't generalize.** `clock_scheduler.py`'s
  Timer-polled edge triggers, the `sys.modules["cocotb.simulator"]`
  patch, and the `python -m cocotb_vivado` subprocess pattern exist
  *because* XSI can't deliver callbacks. They're a XSim-shaped crutch
  with no reuse in any other simulator context.
- **Vivado tool integration (TCL, IP regeneration, project export)
  is vendor-specific** and doesn't belong in cocotb core.
- **No community signal.** No issues in the cocotb/cocotb repo
  mention Vivado, XSim, or Xilinx.
- **Independent release cadence.** Vivado-specific tooling iterates
  on Xilinx releases, not cocotb releases.

The cocotb-blessed pattern for external simulator backends is exactly
what this package does: subclass `cocotb.runner.Simulator`, ship as a
third-party package, register via the project's own `get_runner()`
shim. No fork of cocotb internals; just a backend that follows the
documented integration pattern.

## Submitting changes

- Open PRs against `main`.
- Use the PR template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Every PR must update `CHANGELOG.md` under the appropriate heading
  (`### Added` / `### Changed` / `### Removed` / `### Fixed`). If the
  PR introduces a breaking change, add a row to `MIGRATION.md` as well.
- New public symbols need module / class / function docstrings stating
  their contract (parameters, return value, raises, notable side
  effects). Type hints carry the rest — don't duplicate type
  information in docstring prose.
- Keep comments short and focused on intent. Don't describe history
  (no "previously this returned X" / "renamed from Y"); that belongs
  in commit messages and CHANGELOG.

## License

By contributing, you agree your contributions are licensed under the
[Apache License 2.0](LICENSE).
