#!/usr/bin/env python3
"""Check the installed cocotb against the GPI-shim contract cocotb-vivado relies on.

cocotb-vivado does not use a public API to talk to cocotb: it *replaces*
``cocotb.simulator`` (normally a compiled C extension) with a pure-Python stub
and drives cocotb's GPI interface directly. That interface is private and
unversioned, and it moved materially between cocotb 2.0 and 2.1. This script
introspects the *installed* cocotb and reports any drift from what our stub
provides, so a new cocotb release can be vetted with one command instead of a
mystery crash mid-simulation.

What it checks (statically, no simulator needed):

1. Constants  — every ``cocotb.simulator.<NAME>`` type/edge/range constant
   cocotb references must exist in ``cocotb_vivado._gpi_enums`` (values are
   self-consistent, so only the *names* matter).
2. Functions  — every ``cocotb.simulator.<func>(...)`` cocotb calls must exist
   in our stub, and our function's arity must accept the call (this is what the
   dropped callback ``ud`` argument tripped in 2.1).
3. Imported names — anything cocotb does ``from cocotb.simulator import ...``
   (e.g. the ``gpi_sim_hdl`` ABCs) must be provided.
4. ``pygpi.entry.load_entry`` — we call it with no arguments; flag it if the
   installed signature requires any.

It also prints a reminder list of the contract points that can only be checked
at runtime (callback invocation convention, sim-time/precision marshalling,
scheduler phase model, teardown/atexit, runner exception type) — those are
covered by actually running the test suite against the new cocotb.

Exit code: 0 = compatible, 1 = drift detected (suitable for CI).
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STUB_DIR = REPO_ROOT / "src" / "cocotb_vivado"


# --------------------------------------------------------------------------
# What our stub provides (parsed statically so this never imports our package
# or needs the Vivado libraries).
# --------------------------------------------------------------------------


@dataclass
class Arity:
    """Accepted positional-argument count for one of our stub functions."""

    min: int
    max: float  # math.inf when the function takes *args

    def accepts(self, n: int) -> bool:
        return self.min <= n <= self.max


@dataclass
class Provided:
    names: set[str] = field(default_factory=set)  # every top-level name we export
    func_arity: dict[str, Arity] = field(default_factory=dict)


def _arity_of(fn: ast.FunctionDef) -> Arity:
    a = fn.args
    positional = a.posonlyargs + a.args
    n = len(positional)
    required = n - len(a.defaults)
    return Arity(min=required, max=(float("inf") if a.vararg else n))


def parse_provided() -> Provided:
    """Collect the module-level surface of our stub simulator + enums."""
    provided = Provided()

    def add_module(path: Path, collect_arity: bool) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                provided.names.add(node.name)
                if collect_arity:
                    provided.func_arity[node.name] = _arity_of(node)
            elif isinstance(node, ast.ClassDef):
                provided.names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        provided.names.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                provided.names.add(node.target.id)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    provided.names.add(alias.asname or alias.name)

    add_module(STUB_DIR / "_gpi_enums.py", collect_arity=False)
    add_module(STUB_DIR / "stub" / "simulator.py", collect_arity=True)
    return provided


# --------------------------------------------------------------------------
# What the installed cocotb needs from cocotb.simulator.
# --------------------------------------------------------------------------


@dataclass
class Needs:
    constants: set[str] = field(default_factory=set)  # simulator.<UPPER> refs
    attributes: set[str] = field(default_factory=set)  # simulator.<lower> non-call refs
    calls: dict[str, set[int]] = field(default_factory=dict)  # func -> arg counts seen
    imported: set[str] = field(default_factory=set)  # from cocotb.simulator import ...


def _is_simulator_ref(value: ast.expr) -> bool:
    """True for ``simulator`` or ``cocotb.simulator`` as the base of an attr."""
    if isinstance(value, ast.Name) and value.id == "simulator":
        return True
    return (
        isinstance(value, ast.Attribute)
        and value.attr == "simulator"
        and isinstance(value.value, ast.Name)
        and value.value.id == "cocotb"
    )


class _Scanner(ast.NodeVisitor):
    def __init__(self, needs: Needs) -> None:
        self.needs = needs

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        if isinstance(f, ast.Attribute) and _is_simulator_ref(f.value):
            n_args = len(node.args) + len(node.keywords)
            self.needs.calls.setdefault(f.attr, set()).add(n_args)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if _is_simulator_ref(node.value):
            # Calls are recorded in visit_Call; here record bare references.
            if not getattr(node, "_is_call_func", False):
                (
                    self.needs.constants
                    if node.attr.isupper()
                    else self.needs.attributes
                ).add(node.attr)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "cocotb.simulator":
            for alias in node.names:
                self.needs.imported.add(alias.name)
        self.generic_visit(node)


def scan_cocotb_needs(pkg_dir: Path) -> Needs:
    needs = Needs()
    for path in pkg_dir.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        # Tag Attribute nodes that are the callee of a Call so the visitor
        # doesn't double-count them as bare references.
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                n.func._is_call_func = True  # type: ignore[attr-defined]
        _Scanner(needs).visit(tree)
    # A referenced-but-also-called name is a function, not a bare attribute.
    needs.attributes -= set(needs.calls)
    needs.constants -= set(needs.calls)
    return needs


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--quiet", action="store_true", help="only print drift, not the OK summary"
    )
    args = ap.parse_args()

    try:
        import cocotb  # noqa: PLC0415  (deferred: may be absent)
    except ImportError:
        print("ERROR: cocotb is not installed in this environment.", file=sys.stderr)
        return 2

    pkg_dir = Path(cocotb.__file__).resolve().parent
    version = getattr(cocotb, "__version__", "?")
    provided = parse_provided()
    needs = scan_cocotb_needs(pkg_dir)

    findings: list[str] = []

    # 1. Constants + 3. imported names must all exist in our provided surface.
    for kind, referenced in (
        ("constant", needs.constants),
        ("attribute", needs.attributes),
        ("imported name", needs.imported),
    ):
        for name in sorted(referenced - provided.names):
            findings.append(
                f"[{kind}] cocotb references cocotb.simulator.{name}, "
                f"which our stub does not provide"
            )

    # 2. Functions cocotb calls must exist and our arity must accept the call.
    for name in sorted(needs.calls):
        counts = needs.calls[name]
        if name not in provided.names:
            findings.append(
                f"[function] cocotb calls cocotb.simulator.{name}(), "
                f"which our stub does not define"
            )
            continue
        arity = provided.func_arity.get(name)
        if arity is None:
            continue  # provided as a non-function attribute; can't arity-check
        bad = sorted(n for n in counts if not arity.accepts(n))
        if bad:
            rng = (
                f"{arity.min}"
                if arity.max == arity.min
                else f"{arity.min}..{arity.max}"
            )
            findings.append(
                f"[signature] cocotb calls cocotb.simulator.{name}() with "
                f"{bad} arg(s); our stub accepts {rng}"
            )

    # 4. load_entry() — we call it with zero arguments.
    entry_spec = importlib.util.find_spec("pygpi.entry")
    if entry_spec is not None:
        from pygpi.entry import load_entry  # noqa: PLC0415  (conditional)

        required = [
            p
            for p in inspect.signature(load_entry).parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if required:
            findings.append(
                f"[load_entry] pygpi.entry.load_entry now requires "
                f"{[p.name for p in required]}; __main__ calls load_entry() with none"
            )

    # --- report -----------------------------------------------------------
    print(f"cocotb {version}  ({pkg_dir})")
    print(
        f"scanned: {len(needs.constants)} constants, {len(needs.calls)} called "
        f"functions, {len(needs.imported)} imported names"
    )
    if findings:
        print(f"\nGPI-contract DRIFT — {len(findings)} finding(s):\n")
        for f in findings:
            print(f"  - {f}")
        print(
            "\nThe cocotb GPI shim contract changed. Update "
            "cocotb_vivado/stub/* and _gpi_enums.py, then re-run.\n"
        )
    elif not args.quiet:
        print(
            "\nGPI-contract OK — every referenced constant/function/name is provided."
        )
        print(
            "\nStill verify at runtime (not statically checkable): callback\n"
            "invocation convention (cb() vs cb(ud)), get_sim_time tuple + \n"
            "get_precision exponent, the scheduler phase model, teardown/atexit\n"
            "(xsi.close SIGSEGV), and the runner's failed-build exception type.\n"
            "Run the test suite against this cocotb to cover those.\n"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
