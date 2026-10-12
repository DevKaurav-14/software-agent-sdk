"""Tests for the verify-sdk skill's sdk-map tool and the committed SDK map.

The tool lives at `.agents/skills/verify-sdk/scripts/sdk_map.py`. These tests
run it against throwaway maps and validate the committed map's structure and
cited paths, without running any recipe from the real map.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".agents/skills/verify-sdk/scripts/sdk_map.py"


def _load():
    spec = importlib.util.spec_from_file_location("sdk_map", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["sdk_map"] = module
    spec.loader.exec_module(module)
    return module


sdk_map = _load()

FAMILY = """# Demo family

What a program sees.

Source: `openhands-sdk/openhands/sdk/event/`

Examples: none

## Sub-features

- `S98.ok`: works. Unit: `tests/cross/test_verify_sdk_skill.py`.
- `S98.broken`: fails. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S98.model`: needs a model. Example: `examples/01_standalone_sdk/01_hello_world.py`.
- `S98.gated`: needs Docker. Unit: none. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- Call it.

## Driving it

Preconditions:
- none.

- **Works (`S98.ok`).**
  ```sh
  test 1 = 1
  ```
- **Fails (`S98.broken`).**
  ```sh
  echo before
  false
  ```
- **Model (`S98.model`).**
  ```sh
  uv run python examples/01_standalone_sdk/01_hello_world.py
  ```
- **Docker (`S98.gated`), blocked here.**
  ```sh
  docker ps
  ```

## Gotchas

- none.
"""


def _index(baseline: list[str], rows: str) -> str:
    return (
        "# Map\n\n"
        + "\n".join(baseline)
        + "\n\nThe map has **4 sub-features**, **1 of them untested**.\n\n"
        + "## Families\n\n"
        + rows
        + "\n"
    )


@pytest.fixture
def demo_map(tmp_path, monkeypatch):
    feature_map = tmp_path / "map"
    feature_map.mkdir()
    (feature_map / "S98-demo.md").write_text(FAMILY)
    (feature_map / "README.md").write_text(
        _index(
            ["Maintenance baseline: main@abc1234 (2026-10-01). Keep me."],
            "| S98 | [Demo](S98-demo.md) | x | x | none | 4 | 1 |",
        )
    )
    monkeypatch.setattr(sdk_map, "FEATURE_MAP_DIR", feature_map)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    return feature_map


def _run(capsys, *argv):
    code = sdk_map.main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_committed_map_is_valid(capsys):
    """Structure, IDs, counts, baseline line, and every cited path exists."""
    code, out = _run(capsys, "check")
    assert code == 0, out["problems"]


def test_check_reports_dead_paths_counts_and_undriven_ids(demo_map, capsys):
    family = demo_map / "S98-demo.md"
    family.write_text(
        FAMILY.replace("test_verify_sdk_skill.py`", "test_gone.py`").replace(
            "- **Works (`S98.ok`).**", "- **Works.**"
        )
    )
    code, out = _run(capsys, "check")
    assert code == 1
    problems = out["problems"]["S98-demo.md"]
    assert any("tests/cross/test_gone.py does not exist" in p for p in problems)
    assert "S98.ok has no `Driving it` bullet" in problems

    family.write_text(
        FAMILY.replace(
            "- `S98.gated`:",
            "- `S98.extra`: new. Unit: **none (untested)**.\n- `S98.gated`:",
        ).replace("- **Works (`S98.ok`).**", "- **Works (`S98.ok`, `S98.extra`).**")
    )
    code, out = _run(capsys, "check", "--fix-counts")
    assert out["ok"], out["problems"]
    text = (demo_map / "README.md").read_text()
    assert "| 5 | 2 |" in text
    assert "**5 sub-features**, **2 of them untested**" in text


def test_run_records_pass_fail_blocked_and_skips_model_blocks(
    demo_map, tmp_path, capsys
):
    out_dir = tmp_path / "run"
    code, out = _run(capsys, "run", "--file", "S98", "--out", str(out_dir))
    assert code == 1
    results = {r["ids"][0]: r for r in out["results"]}
    assert results["S98.ok"]["result"] == "pass"
    assert results["S98.broken"]["result"] == "fail"
    assert "before" in Path(results["S98.broken"]["transcript"]).read_text()
    assert results["S98.model"]["result"] == "blocked"
    assert "no LLM_API_KEY" in results["S98.model"]["note"]
    assert results["S98.gated"]["result"] == "blocked"
    ledger = [
        json.loads(line) for line in (out_dir / "ledger.jsonl").read_text().splitlines()
    ]
    assert {r["feature"] for r in ledger} == set(results)

    code, out = _run(capsys, "run", "--file", "S98", "--only", "S98.ok", "--dry-run")
    assert [r["ids"] for r in out["results"]] == [["S98.ok"]]
    code, out = _run(capsys, "run", "--file", "S98", "--only", "S98.nope")
    assert code == 2


def test_report_compares_with_a_baseline_run(demo_map, tmp_path, capsys):
    before, after = tmp_path / "before", tmp_path / "after"
    for path, rows in [
        (before, {"S98.ok": "pass", "S98.broken": "pass", "S98.gated": "blocked"}),
        (after, {"S98.ok": "pass", "S98.broken": "fail", "S98.model": "pass"}),
    ]:
        path.mkdir()
        (path / "ledger.jsonl").write_text(
            "".join(
                json.dumps({"feature": f, "result": r}) + "\n" for f, r in rows.items()
            )
        )
    code, out = _run(
        capsys,
        "report",
        "--runs",
        str(after),
        "--baseline",
        str(before),
        "--print-markdown",
    )
    assert code == 0
    assert [c["feature"] for c in out["changes"]["newly_failing"]] == ["S98.broken"]
    assert [c["feature"] for c in out["changes"]["not_checked"]] == ["S98.gated"]
    assert [c["feature"] for c in out["changes"]["other"]] == ["S98.model"]
    assert out["markdown"].index("S98.broken") < out["markdown"].index("S98.ok")


def test_baseline_reads_and_moves_the_line(demo_map, capsys):
    head = sdk_map.git("rev-parse", "HEAD")
    code, out = _run(capsys, "baseline")
    assert out["sha"] == "abc1234"
    code, out = _run(
        capsys, "baseline", "--set", head, "--date", "2026-10-12", "--main", "HEAD"
    )
    assert code == 0, out
    text = (demo_map / "README.md").read_text()
    assert f"Maintenance baseline: main@{head} (2026-10-12). Keep me." in text


def test_baseline_problems_are_reported(demo_map, capsys):
    (demo_map / "README.md").write_text(
        _index(
            [
                "Maintenance baseline: main@abc1234 (2026-10-01).",
                "Maintenance baseline: main@def5678 (2026-10-02).",
            ],
            "| S98 | [Demo](S98-demo.md) | x | x | none | 4 | 1 |",
        )
    )
    code, out = _run(capsys, "baseline")
    assert code == 1
    assert "2 `Maintenance baseline:` lines" in out["problems"][0]


def test_owners_routes_paths_and_flags_unowned_ones(demo_map, capsys):
    code, out = _run(
        capsys,
        "owners",
        "openhands-sdk/openhands/sdk/event/base.py",
        "openhands-sdk/openhands/sdk/utils/redact.py",
        "docs/readme.md",
    )
    assert out["families"] == ["S98-demo.md"]
    assert out["unowned_product_paths"] == [
        "openhands-sdk/openhands/sdk/utils/redact.py"
    ]


def test_rotation_covers_every_family_once_a_week():
    families = [f"S{n:02d}" for n in range(1, 22)]
    seen = []
    for day in range(10, 17):
        _, today = sdk_map.rotation_slice(families, datetime(2026, 10, day))
        seen += today
    assert sorted(seen) == families


def test_every_command_documents_examples(capsys):
    parser = sdk_map.build_parser()
    for name in ("check", "ids", "owners", "baseline", "rotation", "run", "report"):
        with pytest.raises(SystemExit):
            parser.parse_args([name, "--help"])
        assert "Examples:" in capsys.readouterr().out, name
