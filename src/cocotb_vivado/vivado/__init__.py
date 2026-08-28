# Copyright cocotb-vivado contributors
# Licensed under the Apache License 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Vivado-managed source types and tool-driver helpers.

This package is the home for everything that invokes the full Vivado
tool (``vivado -mode batch``). Architectural rule, enforceable in
review: if you're adding ``subprocess.run([..., "vivado", ...])``, it
belongs here, not in :mod:`cocotb_vivado.runner`.

The public surface is a small class hierarchy used by the runner's
``sources=`` list. Pick the class by input file format:

==========================  ===================  ===================================
Input                       Class                Vivado mechanism
==========================  ===================  ===================================
``.xci``                    :class:`VivadoIp`    ``add_files; export_ip_user_files``
``.bd``                     :class:`VivadoBd`    ``make_wrapper; launch_simulation``
``.xpr``                    :class:`VivadoProject`  ``open_project; launch_simulation``
``.tcl`` / pre-extracted    :class:`VivadoExportedSim`  runs your TCL
==========================  ===================  ===================================

* :class:`VivadoSource` — abstract base.
* :class:`VivadoIp` — one or more ``.xci`` IP cores. Runs
  ``set_part; add_files -norecurse; export_ip_user_files``.
* :class:`VivadoBd` — a ``.bd`` block design. Runs
  ``make_wrapper -top -import`` (to flatten interface ports) +
  ``launch_simulation -scripts_only`` in a throwaway project.
* :class:`VivadoProject` — a ``.xpr`` project. Runs
  ``open_project; launch_simulation -scripts_only -absolute_path``.
* :class:`VivadoExportedSim` — a user-supplied TCL script that
  produces a ``sim_export``-style directory itself.

Each subclass exposes ``.prepare(build_dir, hdl_library) -> SimDirInfo``,
which (re)runs the Vivado batch when out-of-date and returns the
distilled view of the resulting ``.prj`` files plus the xelab
command-line extracted from the sibling ``*.sh`` script.

Sub-module layout:

* ``sources`` — the :class:`VivadoSource` hierarchy.
* ``sim_dir`` — :class:`SimDirInfo` + :func:`read_sim_dir` parser.
* ``part`` — :func:`discover_default_part` and friends.
* ``_tcl`` — package-private wrappers around the ``vivado`` binary.
"""

from .part import discover_default_part
from .sim_dir import SimDirInfo, read_sim_dir
from .sources import (
    VivadoBd,
    VivadoExportedSim,
    VivadoIp,
    VivadoProject,
    VivadoSource,
)

__all__ = [
    "SimDirInfo",
    "VivadoBd",
    "VivadoExportedSim",
    "VivadoIp",
    "VivadoProject",
    "VivadoSource",
    "discover_default_part",
    "read_sim_dir",
]
