# Copyright cocotb-vivado contributors
# Licensed under the Apache License 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Part-number discovery and resolution.

:func:`discover_default_part` is the opt-in helper that queries
Vivado for an installed part and caches the answer.
:func:`_resolve_part_num` resolves a kwarg + env-var to a part name
used internally by :class:`cocotb_vivado.vivado.VivadoIp`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ._tcl import DISCOVER_PART_TCL, assert_vivado_on_path

_DEFAULT_PART_CACHE = Path.home() / ".cache" / "cocotb-vivado" / "default_part"


def discover_default_part(cache_file: Path | None = None, force: bool = False) -> str:
    """Discover a Vivado part installed locally and cache it.

    Runs ``vivado -mode batch`` once, asks it for ``[lindex [get_parts]
    0]``, and writes the result to ``~/.cache/cocotb-vivado/default_part``
    so the next call is free. Opt-in: nothing in cocotb-vivado invokes
    this automatically. Users pass the result as
    ``VivadoIp(..., part_num=...)`` or populate
    ``COCOTB_DEFAULT_PART_NUM`` from it.

    Args:
        cache_file: Where to read/write the cached part name. Defaults
            to ``~/.cache/cocotb-vivado/default_part``.
        force: If ``True``, ignore any cached value and re-run Vivado.

    Returns:
        The discovered part name (e.g. ``"xc7a35tcpg236-1"``).

    Raises:
        SystemExit: if ``vivado`` is missing from ``PATH`` or the
            discovery TCL fails.
        RuntimeError: if the TCL ran but no part name could be parsed
            from the output.
    """
    target = Path(cache_file) if cache_file is not None else _DEFAULT_PART_CACHE
    if not force and target.exists():
        cached = target.read_text(encoding="utf-8").strip()
        if cached:
            return cached

    assert_vivado_on_path()

    target.parent.mkdir(parents=True, exist_ok=True)
    tcl_path = target.parent / "discover_part.tcl"
    tcl_path.write_text(DISCOVER_PART_TCL, encoding="utf-8")

    result = subprocess.run(
        ["vivado", "-mode", "batch", "-source", str(tcl_path), "-nolog", "-nojournal"],
        cwd=str(target.parent),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Process 'vivado' terminated with error {result.returncode} "
            f"during part discovery"
        )

    part: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("DISCOVERED_PART="):
            part = line.split("=", 1)[1].strip()
            break
    if not part:
        raise RuntimeError(
            "Part discovery TCL ran but no DISCOVERED_PART line was emitted. "
            "Check the Vivado output for licensing or device-installation issues."
        )

    target.write_text(part + "\n", encoding="utf-8")
    return part


def _resolve_part_num(part_num: str | None) -> str | None:
    """Return ``part_num`` if given, else ``COCOTB_DEFAULT_PART_NUM`` env, else ``None``."""
    if part_num is not None:
        return part_num
    env_value = os.environ.get("COCOTB_DEFAULT_PART_NUM")
    if env_value:
        return env_value
    return None
