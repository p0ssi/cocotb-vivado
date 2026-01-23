import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
from typing import Optional

from cocotb.runner import outdated


class Xpr:
    SIM_TYPE = "xsim"

    def __init__(self, xpr_path: str|Path, hdl_toplevel: str, build_dir: str|Path = "."):
        if shutil.which("vivado") is None:
            raise SystemExit("ERROR: vivado executable not found in path!")

        self.hdl_toplevel = hdl_toplevel
        self.build_dir = Path(build_dir).resolve()
        self.xpr_path = Path(xpr_path).resolve()
        self.export_dir = None
        self.simulator_dir = None
        self.simulator_script = None
        self.dll_path = None
        self.always: bool = False

    def build(self, export_dir: str | Path | None = None, always: bool = None) -> Path:
        self.export_dir = Path(export_dir) if export_dir else self.build_dir / "sim_export"
        self.always = always

        self.simulator_dir = self.export_dir / self.SIM_TYPE
        self.simulator_script = self.simulator_dir / (self.hdl_toplevel + get_batch_ext())

        if outdated(self.simulator_script, [self.xpr_path]) or self.always:
            self._export_sim()  # export the simulator

        self.dll_path = self.simulator_dir / "xsim.dir" / self.hdl_toplevel / ("xsimk" + get_dll_ext())
        if outdated(self.dll_path, [self.simulator_dir]) or self.always:
            self._build_dll()   # build to a shared object

        return self.dll_path

    def _export_sim(self):
        # delete the export dir if it exists
        if self.export_dir.exists():
            shutil.rmtree(self.export_dir)

        self._execute_tcl(
            f"open_project {str(self.xpr_path)}",
            f"export_simulation -directory {str(self.export_dir)} -absolute_path -simulator {self.SIM_TYPE} -force -more_options [list xsim.elaborate.xelab:--dll]",
            "close_project",
            "exit"
        )

    def _build_dll(self):

        for step in ["compile", "elaborate"]:
            subprocess.run(
                [str(self.simulator_script), "-step", step],
                cwd=self.simulator_dir
            )

    def _execute_tcl(self, *tcl_cmds: str) -> str:
        return execute_tcl(list(tcl_cmds), cwd=self.build_dir)

def execute_tcl(source: list[str] | Path | str, output: Optional[Path|str] = None, cwd: Optional[Path|str] = None) -> str|None:
    """
    Execute a Vivado Tcl script and return its standard output.

    This function runs Xilinx Vivado in batch mode with `-nolog -nojournal -notrace`.
    If `source` is a list of Tcl commands, they are written to a temporary `.tcl`
    file which is then executed. If `source` is a `str` or `Path`, it is treated as
    a path to an existing Tcl script. The function prints `source` to stdout for
    visibility and returns Vivado's stdout on success.

    Args:
        source: Either:
            * A list of Tcl command strings to be executed, or
            * A string/`Path` pointing to a Tcl script file.
        output: Optional output file, of which timestamp if compared against source
            file timestamp. The script is only executed if the output is outdated.
        cwd: Optional working directory to run Vivado from. If `None`, the current
            process working directory is used.

    Returns:
        The standard output (`str`) produced by the Vivado process, or None if the
        output file was already up-to-date.

    Raises:
        SystemExit: If the Vivado process exits with a non-zero return code.
    """
    if cwd is None:
        cwd=Path()  # current dir

    def execute(file_name):
        if not Path(file_name).is_file():
            raise FileNotFoundError(f"TCL script '{file_name}' does not exist or is not a file")
        process = subprocess.run(
            ["vivado", "-nolog", "-nojournal", "-notrace", "-mode", "batch", "-source", file_name],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            if output:
                # remove the output artifact to force re-run
                out_path = Path(output)
                out_path.unlink(missing_ok=True)
            raise RuntimeError(process.stderr)
        return process.stdout

    if isinstance(source, list):
        # source if list of commands
        with tempfile.NamedTemporaryFile("w", suffix=".tcl") as tf:
            for cmd in source:
                tf.write(cmd + "\n")
            tf.flush()
            return execute(tf.name)

    # file source
    src_path = Path(source)

    if output:
        out_path = Path(output)
        if not outdated(out_path, [src_path]):
            return None

    return execute(str(src_path))

def get_dll_ext() -> str:
    if sys.platform.startswith("win"):
        return ".dll"
    elif sys.platform.startswith("linux"):
        return ".so"
    else:
        raise RuntimeError(f"Unknown platform {sys.platform}")

def get_batch_ext() -> str:
    if sys.platform.startswith("win"):
        return ".bat"
    elif sys.platform.startswith("linux"):
        return ".sh"
    else:
        raise RuntimeError(f"Unknown platform {sys.platform}")
