import os
import shutil
from typing import List, Mapping

import cocotb
from cocotb.runner import Command, Simulator, UnknownFileExtension, is_vhdl_source, is_verilog_source, outdated
from cocotb.runner import get_runner as get_runner_orig

from .stub.mgr import Mgr
from .vivado import Xpr


class Vivado(Simulator):
    supported_gpi_interfaces = {"verilog": ["xsi"]}

    def __init__(self) -> None:
        super().__init__()
        self.sim_shlib_path = None
        self.xpr = None

    @staticmethod
    def _simulator_in_path() -> None:
        for exe in ["xvhdl", "xvlog", "xelab"]:
            if shutil.which(exe) is None:
                raise SystemExit(f"ERROR: {exe} executable not found in path!")

    def _build_command(self) -> List[Command]:
        # default location for shared object
        self.sim_shlib_path = self.build_dir / "xsim.dir" / self._get_top_module_name() / "xsimk.so"

        # check if sources contain .xpr
        if len(self.sources) == 1:
            if self.sources[0].suffix == ".xpr":
                self.xpr = Xpr(
                    xpr_path=self.sources[0],
                    hdl_toplevel=self.hdl_toplevel,
                    build_dir=self.build_dir,
                )
                self.sim_shlib_path = self.xpr.build(
                    always=self.always,
                )
                return []

        # sort the sources into vhdl and verilog
        for source in self.sources:
            if is_vhdl_source(source):
                self.vhdl_sources.append(source)
            elif is_verilog_source(source):
                self.verilog_sources.append(source)
            else:
                raise UnknownFileExtension(source)

        if not outdated(self.sim_shlib_path, self.verilog_sources + self.vhdl_sources) and not self.always:
            return []  # no changes to sources, don't rebuild

        xelab_args = list(self.build_args)
        xelab_args += ["-dll"]
        xelab_args += self._get_parameter_options(self.parameters)
        if self.waves:
            xelab_args += ["-debug", "typical"]

        cmds = []
        compile_args = ["-work", self.hdl_library]
        if self.vhdl_sources:
            vhdl_sources = [str(src_file) for src_file in self.vhdl_sources]
            cmds.append(
                ["xvhdl", "--2008"] + compile_args + vhdl_sources
            )
        if self.verilog_sources:
            verilog_sources = [str(src_file) for src_file in self.verilog_sources]
            cmds.append(["xvlog"] + compile_args + verilog_sources)
        if cmds:
            cmds.append(["xelab"] + xelab_args + [self._get_top_module_name()])

        return cmds

    def _get_parameter_options(self, parameters: Mapping[str, object]) -> Command:
        out: Command = []
        for name, value in parameters.items():
            out += ["-generic_top", f"{name}={value}"]
        return out

    def _test_command(self) -> List[Command]:
        # bluntly misuse this method to execute simulator in Python rather than in a subprocess
        if self.hdl_toplevel_lang != "verilog":
            raise RuntimeError("Only verilog supported as top level language")

        # store environment variables required by the tests
        os.environ["MODULE"] = self.test_module
        test = self.current_test_name
        os.environ["COCOTB_RESULTS_FILE"] = self.env["COCOTB_RESULTS_FILE"]

        tracefile = self.build_dir / "xsi.wdb" if self.waves else None

        mgr = Mgr.init(self.sim_shlib_path, tracefile=tracefile)

        cocotb._initialise_testbench([])
        mgr.run()
        mgr.close()

        return []  # no commands to execute

    def _get_top_module_name(self):
        return self.hdl_library + "." + self.hdl_toplevel

def get_runner(sim_name):
    if sim_name == "vivado":
        return Vivado()
    return get_runner_orig(sim_name)
