"""Tier 1 build-cache mechanics tests.

Most scenarios are unit-style — exercise hashing, signature
serialization, and per-VivadoSource fingerprint() output directly,
without invoking ``runner.build()``. One end-to-end integration test
proves the cache hit/miss path through the runner; it's gated on
Vivado availability and only runs locally.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import pytest

from cocotb_vivado.runner import (
    SIGNATURE_FILENAME,
    SIGNATURE_SCHEMA_VERSION,
    _hash_file,
    _load_signature,
    _save_signature,
    get_runner,
    get_xsim_tool_versions,
)
from cocotb_vivado.vivado import VivadoExportedSim, VivadoIp, VivadoProject
from cocotb_vivado.vivado.sources import _hash_dir

# ---------------------------------------------------------------------------
# Primitives: _hash_file, _hash_dir, get_xsim_tool_versions
# ---------------------------------------------------------------------------


def test_hash_file_missing_returns_empty(tmp_path: Path) -> None:
    assert _hash_file(tmp_path / "nope") == ""


def test_hash_file_content_changes_invalidate(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    a = _hash_file(f)
    f.write_text("hello!")
    b = _hash_file(f)
    assert a != b and len(a) == 64 and len(b) == 64


def test_hash_file_touch_only_keeps_hash(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello")
    a = _hash_file(f)
    os.utime(f, (1_000_000, 1_000_000))
    assert _hash_file(f) == a  # mtime change, content same


def test_hash_dir_manifest_changes_on_content(tmp_path: Path) -> None:
    d = tmp_path / "tree"
    d.mkdir()
    (d / "a.txt").write_text("aa")
    (d / "b.txt").write_text("bb")
    a = _hash_dir(d)
    (d / "b.txt").write_text("bbX")
    assert _hash_dir(d) != a


def test_hash_dir_missing_returns_empty(tmp_path: Path) -> None:
    assert _hash_dir(tmp_path / "absent") == ""


# ---------------------------------------------------------------------------
# Signature file roundtrip and error tolerance
# ---------------------------------------------------------------------------


def test_signature_roundtrip(tmp_path: Path) -> None:
    sig = {"schema_version": 1, "kwargs": {"a": 1}}
    p = tmp_path / SIGNATURE_FILENAME
    _save_signature(p, sig)
    assert _load_signature(p) == sig


def test_signature_corrupt_returns_none(tmp_path: Path) -> None:
    p = tmp_path / SIGNATURE_FILENAME
    p.write_text("{not json")
    assert _load_signature(p) is None


def test_signature_absent_returns_none(tmp_path: Path) -> None:
    assert _load_signature(tmp_path / SIGNATURE_FILENAME) is None


# ---------------------------------------------------------------------------
# VivadoSource.fingerprint() — pure dict-shape tests, no Vivado required
# ---------------------------------------------------------------------------


def test_vivado_ip_fingerprint_with_builder_tcl(tmp_path: Path) -> None:
    tcl = tmp_path / "regen.tcl"
    tcl.write_text("create_ip ...\n")
    src = VivadoIp(
        "ip/x.xci",
        builder_tcl=tcl,
        part_num="xczu7eg-ffvc1156-2-e",
    )
    fp = src.fingerprint()
    assert fp["kind"] == "VivadoIp"
    # builder_tcl set → paths recorded as identifiers (strings), not hashed
    assert fp["paths"] == ["ip/x.xci"]
    assert fp["builder_tcl"]["sha256"] == _hash_file(tcl)
    assert fp["part_num"] == "xczu7eg-ffvc1156-2-e"


def test_vivado_ip_fingerprint_without_builder_tcl(tmp_path: Path) -> None:
    xci = tmp_path / "y.xci"
    xci.write_text("<xci>...</xci>")
    src = VivadoIp(xci, part_num="xczu7eg-ffvc1156-2-e")
    fp = src.fingerprint()
    assert fp["builder_tcl"] is None
    # No builder_tcl → XCI itself must be hashed
    assert fp["paths"][0]["sha256"] == _hash_file(xci)


def test_vivado_ip_fingerprint_changes_on_part_num() -> None:
    a = VivadoIp("ip/x.xci", part_num="xczu7eg-ffvc1156-2-e").fingerprint()
    b = VivadoIp("ip/x.xci", part_num="xczu9eg-ffvb1156-2-e").fingerprint()
    assert a != b


def test_vivado_project_fingerprint_with_builder_tcl(tmp_path: Path) -> None:
    tcl = tmp_path / "build.tcl"
    tcl.write_text("create_project ...")
    src = VivadoProject(xpr_path="proj/proj.xpr", builder_tcl=tcl)
    fp = src.fingerprint()
    assert fp["kind"] == "VivadoProject"
    assert fp["xpr"] == "proj/proj.xpr"  # string identifier
    assert fp["builder_tcl"]["sha256"] == _hash_file(tcl)


def test_vivado_project_fingerprint_changes_on_part_num_override(
    tmp_path: Path,
) -> None:
    """Distinct part_num must invalidate VivadoProject's signature."""
    tcl = tmp_path / "b.tcl"
    tcl.write_text("x")
    a = VivadoProject(
        xpr_path="p.xpr", builder_tcl=tcl, part_num="xczu7eg-ffvc1156-2-e"
    ).fingerprint()
    b = VivadoProject(
        xpr_path="p.xpr", builder_tcl=tcl, part_num="xczu9eg-ffvb1156-2-e"
    ).fingerprint()
    assert a != b


def test_vivado_exported_sim_fingerprint_with_tcl(tmp_path: Path) -> None:
    tcl = tmp_path / "e.tcl"
    tcl.write_text("launch_simulation ...")
    src = VivadoExportedSim(tcl_file=tcl)
    fp = src.fingerprint()
    assert fp["kind"] == "VivadoExportedSim"
    assert fp["tcl_file"]["sha256"] == _hash_file(tcl)


def test_vivado_exported_sim_fingerprint_without_tcl(tmp_path: Path) -> None:
    """tcl_file=None → identity is the result_dir's content manifest."""
    rdir = tmp_path / "sim"
    (rdir / "xsim").mkdir(parents=True)
    (rdir / "xsim" / "elaborate.sh").write_text("xelab ...")
    src = VivadoExportedSim(tcl_file=None, result_dir=rdir)
    fp = src.fingerprint()
    assert fp["tcl_file"] is None
    assert fp["result_dir"]["sha256"] == _hash_dir(rdir)


# ---------------------------------------------------------------------------
# get_xsim_tool_versions — smoke-test that it returns the expected key shape
# ---------------------------------------------------------------------------


def test_get_xsim_tool_versions_shape() -> None:
    versions = get_xsim_tool_versions()
    assert set(versions.keys()) == {"xelab", "xvlog", "xvhdl"}
    # values are strings (possibly empty if tools aren't on PATH)
    assert all(isinstance(v, str) for v in versions.values())


# ---------------------------------------------------------------------------
# End-to-end cache integration: build twice, assert hit on second run
# ---------------------------------------------------------------------------


def _vivado_on_path() -> bool:
    return all(shutil.which(t) for t in ("xelab", "xvlog", "xvhdl"))


@pytest.mark.skipif(not _vivado_on_path(), reason="vivado XSim binaries not on PATH")
def test_cache_hit_skips_pipeline_on_second_build(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proj_path = Path(__file__).resolve().parent
    runner = get_runner("vivado")

    common_kwargs = {
        "sources": [proj_path / "tb.v"],
        "hdl_toplevel": "tb",
        "always": False,
        "timescale": ("1ns", "1ps"),
        "build_dir": str(tmp_path),
    }

    # Cold cache: signature is absent → expect a miss + xvlog/xelab run.
    with caplog.at_level(logging.INFO, logger="cocotb_vivado.runner.cache"):
        runner.build(**common_kwargs)
        assert any("cache miss" in r.message for r in caplog.records), (
            "first build should miss the cache"
        )

    # Signature file should now exist and have the expected schema.
    sig_path = tmp_path / SIGNATURE_FILENAME
    assert sig_path.exists()
    sig = _load_signature(sig_path)
    assert sig is not None
    assert sig["schema_version"] == SIGNATURE_SCHEMA_VERSION

    # Warm cache: same inputs → expect a hit.
    caplog.clear()
    snapshot_mtime_before = (tmp_path / "xsim.dir" / "tb" / "xsimk.so").stat().st_mtime
    with caplog.at_level(logging.INFO, logger="cocotb_vivado.runner.cache"):
        runner.build(**common_kwargs)
        assert any("cache hit" in r.message for r in caplog.records), (
            "second build with identical inputs should hit the cache"
        )

    # Cache hit must not touch the snapshot artifact.
    snapshot_mtime_after = (tmp_path / "xsim.dir" / "tb" / "xsimk.so").stat().st_mtime
    assert snapshot_mtime_before == snapshot_mtime_after


@pytest.mark.skipif(not _vivado_on_path(), reason="vivado XSim binaries not on PATH")
def test_cache_miss_on_parameters_change(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proj_path = Path(__file__).resolve().parent
    runner = get_runner("vivado")

    # Initial build with one parameter set; uses tb_params.v whose
    # WIDTH parameter is honored by -generic_top.
    runner.build(
        sources=[proj_path / "tb_params.v"],
        hdl_toplevel="tb_params",
        parameters={"WIDTH": 8},
        always=False,
        timescale=("1ns", "1ps"),
        build_dir=str(tmp_path),
    )
    sig_a = _load_signature(tmp_path / SIGNATURE_FILENAME)

    # Change a parameter; rebuild.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="cocotb_vivado.runner.cache"):
        runner.build(
            sources=[proj_path / "tb_params.v"],
            hdl_toplevel="tb_params",
            parameters={"WIDTH": 16},
            always=False,
            timescale=("1ns", "1ps"),
            build_dir=str(tmp_path),
        )
    sig_b = _load_signature(tmp_path / SIGNATURE_FILENAME)

    assert sig_a != sig_b, "parameter change should rewrite the signature"
    assert any("cache miss: signature mismatch" in r.message for r in caplog.records), (
        "parameter change should report mismatch"
    )


@pytest.mark.skipif(not _vivado_on_path(), reason="vivado XSim binaries not on PATH")
def test_cache_miss_when_snapshot_deleted(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proj_path = Path(__file__).resolve().parent
    runner = get_runner("vivado")
    common_kwargs = {
        "sources": [proj_path / "tb.v"],
        "hdl_toplevel": "tb",
        "always": False,
        "timescale": ("1ns", "1ps"),
        "build_dir": str(tmp_path),
    }
    runner.build(**common_kwargs)

    # Delete the snapshot but leave build_signature.json in place.
    shutil.rmtree(tmp_path / "xsim.dir")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="cocotb_vivado.runner.cache"):
        runner.build(**common_kwargs)
        assert any("snapshot artifact missing" in r.message for r in caplog.records), (
            "deleted snapshot must trigger a cache miss"
        )


@pytest.mark.skipif(not _vivado_on_path(), reason="vivado XSim binaries not on PATH")
def test_cache_corrupt_signature_treated_as_miss(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proj_path = Path(__file__).resolve().parent
    runner = get_runner("vivado")
    common_kwargs = {
        "sources": [proj_path / "tb.v"],
        "hdl_toplevel": "tb",
        "always": False,
        "timescale": ("1ns", "1ps"),
        "build_dir": str(tmp_path),
    }
    # Pre-create a corrupt signature; should be silently treated as miss.
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / SIGNATURE_FILENAME).write_text("{not json")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="cocotb_vivado.runner.cache"):
        runner.build(**common_kwargs)
        assert any(
            "signature absent or unreadable" in r.message for r in caplog.records
        )
