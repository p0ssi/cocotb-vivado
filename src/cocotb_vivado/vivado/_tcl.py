# Copyright cocotb-vivado contributors
# Licensed under the Apache License 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Low-level helpers for invoking ``vivado -mode batch``.

Package-private (leading underscore on the module name). Callers
inside ``cocotb_vivado.vivado`` use these; external callers should go
through the public source classes.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

EXPORT_SCRIPTS_TCL = """\
launch_simulation -scripts_only -absolute_path
exit
"""

DISCOVER_PART_TCL = """\
puts "DISCOVERED_PART=[lindex [get_parts] 0]"
exit
"""


def assert_vivado_on_path() -> None:
    """Raise ``SystemExit`` if the ``vivado`` binary is not on ``PATH``."""
    if shutil.which("vivado") is None:
        raise SystemExit(
            "ERROR: 'vivado' executable not found in PATH. "
            "Source the Vivado settings64.sh from your install."
        )


def ensure_xsim_ini(build_dir: Path) -> Path | None:
    """Provision ``xsim.ini`` in ``build_dir`` so xelab finds precompiled libs.

    Vivado ships a default ``xsim.ini`` at
    ``$XILINX_VIVADO/data/xsim/xsim.ini`` that maps every precompiled
    Xilinx library (xpm, secureip, unisims_ver, blk_mem_gen_*,
    smartconnect_*, ...) to its on-disk location. xelab auto-detects
    ``xsim.ini`` in its cwd, so we copy that file into ``build_dir``
    once and the runner's xelab invocation resolves the same library
    references Vivado's own scripts would.

    No-op if ``build_dir/xsim.ini`` already exists (user-provided or
    from a prior build). No-op with a logged warning if
    ``$XILINX_VIVADO`` is unset or the source ini is missing —
    pure-RTL builds don't need xsim.ini at all.

    Args:
        build_dir: The runner's working directory.

    Returns:
        Path to the provisioned ini file, or ``None`` if none could be
        located (pure-RTL elaboration still works without it).
    """
    target = build_dir / "xsim.ini"
    if target.exists():
        return target
    xilinx_vivado = os.environ.get("XILINX_VIVADO")
    if not xilinx_vivado:
        log.warning(
            "XILINX_VIVADO not set; skipping xsim.ini provisioning. "
            "Precompiled Xilinx libraries will not be resolvable at "
            "elaboration time."
        )
        return None
    source = Path(xilinx_vivado) / "data" / "xsim" / "xsim.ini"
    if not source.exists():
        log.warning("%s does not exist; skipping xsim.ini provisioning.", source)
        return None
    shutil.copy2(source, target)
    return target


def execute_tcl(
    tcl_files: list[Path],
    cwd: Path,
    tcl_mode: str = "batch",
) -> None:
    """Run ``vivado -mode <tcl_mode>`` against the listed TCL files."""
    for tcl_file in tcl_files:
        assert tcl_file.exists(), f"TCL file {tcl_file} does not exist"

    assert_vivado_on_path()

    source_args: list[str] = []
    for tcl_file in tcl_files:
        source_args.extend(["-source", str(tcl_file.resolve())])

    cmd = ["vivado", "-mode", tcl_mode, *source_args]
    log.info("Running command %s in directory %s", " ".join(cmd), cwd)
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"Process {cmd[0]!r} terminated with error {result.returncode}"
        )
