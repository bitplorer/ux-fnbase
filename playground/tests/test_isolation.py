"""Import-graph Isolation Law. Fail closed on law break."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UX_FNBASE_SRC = ROOT / "src" / "ux_fnbase"
PLAYGROUND = ROOT / "playground"


def _py_files(root: Path):
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_ux_fnbase_does_not_import_compose_or_playground():
    banned = {"ux_compose", "ux_behavior", "ux_channel", "ux_dom", "playground"}
    offenders = []
    for path in _py_files(UX_FNBASE_SRC):
        hit = _imported_modules(path) & banned
        for name in sorted(hit):
            offenders.append(f"{path.relative_to(ROOT)}:{name}")
    assert offenders == []


def test_wire_does_not_import_compose_or_channel():
    banned = {"ux_compose", "ux_behavior", "ux_channel", "ux_dom"}
    offenders = []
    for path in _py_files(PLAYGROUND / "wire"):
        names = _imported_modules(path)
        hit = names & banned
        for name in sorted(hit):
            offenders.append(f"{path.relative_to(ROOT)}:{name}")
        if path.name in {"bind.py", "live.py", "intent.py"} and "playground" in names:
            offenders.append(f"{path.relative_to(ROOT)}:playground")
    assert offenders == []


def test_host_does_not_import_channel():
    names = _imported_modules(PLAYGROUND / "host.py")
    assert "ux_channel" not in names
    assert "ux_compose" not in names
