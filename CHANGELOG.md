# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `cocotb_vivado.runner` — a Python runner subclass of
  `cocotb.runner.Simulator`. Reachable via
  `cocotb_vivado.runner.get_runner("vivado")` and the standard
  `runner.build()` / `runner.test()` interface. Pure XSim binary
  orchestration: only `xelab` / `xvlog` / `xvhdl` are invoked
  directly. Vivado-managed sources (`.xci`, `.bd`, `.xpr`) are out
  of scope and land in a follow-up PR.
- `cocotb_vivado.__main__` — subprocess entry point that
  `runner.test()` spawns via `python -m cocotb_vivado`. Reads the
  snapshot name and optional WDB output path from environment.
- `wdb_file` kwarg threaded through `xsi.XSI.__init__` and
  `stub.mgr.Mgr.init`, so the WDB output path can be set explicitly
  by the runner instead of defaulting to `xsi.wdb` in the cwd.
- `pyproject.toml` mirroring cocotb upstream's lint and type
  configuration (ruff with the same extend-select / ignore set, mypy
  in strict mode with per-module overrides for the legacy modules,
  pytest with `--strict-markers`).
- `.pre-commit-config.yaml` with `ruff --fix`, `ruff-format`, basic
  whitespace/EOL fixers, and `validate-pyproject`.
- GitHub Actions workflow `.github/workflows/lint.yml` running ruff
  and mypy on every push/PR.
- `CONTRIBUTING.md` describing the Linux-only dev setup, the
  runner-stays-on-XSim-binaries architectural rule, and the
  submission convention.
- `CHANGELOG.md` (this file) and `MIGRATION.md` (before/after
  guidance for users moving off the legacy `cocotb_vivado.run()`
  path).
- `.github/PULL_REQUEST_TEMPLATE.md` with required sections for
  behavioral summary, breaking changes, local test output, and the
  documentation-diff checklist.
- `examples/counter/`, `examples/parameters/`, and `examples/ip/`
  (placeholder until IP / BD / XPR support lands).
- `tests/test_params.py` + `tests/tb_params.v` — verify top-level
  Verilog parameter / VHDL generic pass-through to `xelab` via
  `-generic_top`.

### Changed

- `tests/test_simple.py` and `tests/test_tb.py` rewritten on top of
  `cocotb_vivado.runner.get_runner()`. Their legacy
  `cocotb_vivado.run()`-based variants stay available but are
  skip-gated behind `COCOTB_VIVADO_TEST_DIRECT=1`.
- `tests/test_axil.py`, `tests/test_fw.py`, `tests/test_xsi.py`
  module-level skip-gated behind `COCOTB_VIVADO_TEST_DIRECT=1` while
  they still depend on the legacy direct-launch path. They will
  migrate to the new runner alongside IP / BD / XPR support.
- `setup.py` reduced to a thin shim; project metadata moved to the
  `[project]` table in `pyproject.toml`.
