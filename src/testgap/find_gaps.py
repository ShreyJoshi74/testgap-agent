"""find_gaps — parse coverage JSON, map missing lines to functions, rank them.

Public API
----------
    main(project, label, src) -> int
    score_gap(missing_count, is_public, in_docs) -> int
    priority_label(score) -> str
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple

from testgap.common import load_json, reports_dir, save_json, to_posix


# ---------------------------------------------------------------------------
# Pure scoring functions (tested independently)
# ---------------------------------------------------------------------------

def score_gap(missing_count: int, is_public: bool, in_docs: bool) -> int:
    """Compute the priority score for a gap.

    score = missing_count × (2 if public else 1) + (10 if in_docs else 0)
    """
    return missing_count * (2 if is_public else 1) + (10 if in_docs else 0)


def priority_label(score: int) -> str:
    """Return ``'high'``, ``'medium'``, or ``'low'`` for a score."""
    if score >= 20:
        return "high"
    if score >= 8:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

class _FuncInfo(NamedTuple):
    name: str           # fully qualified: "ClassName.method" or "func"
    start_line: int     # first decorator line (or def line if no decorator)
    end_line: int


def _collect_functions(source: str) -> list[_FuncInfo]:
    """Return all FunctionDef / AsyncFunctionDef nodes in *source*.

    - Methods are named ``ClassName.method``.
    - Nested functions are named with their full dot path.
    - ``start_line`` is the line of the first decorator if present, else the
      ``def`` line (coverage.py counts decorator lines).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    funcs: list[_FuncInfo] = []

    def _visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                _visit(child, child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{prefix}.{child.name}" if prefix else child.name
                if child.decorator_list:
                    start = child.decorator_list[0].lineno
                else:
                    start = child.lineno
                funcs.append(_FuncInfo(
                    name=qual,
                    start_line=start,
                    end_line=child.end_lineno,
                ))
                # Recurse for nested functions — use qual as new prefix
                _visit(child, qual)

    _visit(tree, "")
    return funcs


def _innermost_function(
    line: int, funcs: list[_FuncInfo]
) -> _FuncInfo | None:
    """Return the innermost function that contains *line*, or None."""
    candidates = [
        f for f in funcs if f.start_line <= line <= f.end_line
    ]
    if not candidates:
        return None
    # Innermost = smallest span (end_line - start_line)
    return min(candidates, key=lambda f: f.end_line - f.start_line)


# ---------------------------------------------------------------------------
# Documentation search
# ---------------------------------------------------------------------------

def _mentioned_in_docs(func_name: str, project: Path) -> bool:
    """Return True if *func_name* appears as a whole word in any doc file.

    Searches ``<project>/README.md`` and ``<project>/docs/**/*.md``.
    For ``ClassName.method`` style names, matches the method-name part only.
    """
    # For "ClassName.method" style, match the method part for doc search
    search_name = func_name.split(".")[-1]
    pattern = re.compile(r"\b" + re.escape(search_name) + r"\b")

    candidates: list[Path] = []
    readme = project / "README.md"
    if readme.exists():
        candidates.append(readme)
    docs_dir = project / "docs"
    if docs_dir.is_dir():
        candidates.extend(docs_dir.rglob("*.md"))

    for doc_path in candidates:
        try:
            text = doc_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Public check
# ---------------------------------------------------------------------------

def _is_public(func_name: str) -> bool:
    """Return True if the function (or method) is considered public.

    Public = simple name doesn't start with ``_``, OR is a dunder.
    For ``Class.method`` names, check the method part.
    """
    leaf = func_name.split(".")[-1]
    if leaf.startswith("__") and leaf.endswith("__"):
        return True  # dunder is public
    return not leaf.startswith("_")


# ---------------------------------------------------------------------------
# Reason builder
# ---------------------------------------------------------------------------

def _build_reason(
    func_name: str,
    missing_count: int,
    is_public: bool,
    in_docs: bool,
    doc_source: str,
) -> str:
    """Build a human-readable reason string."""
    parts: list[str] = []
    if is_public:
        parts.append("Public function")
    else:
        parts.append("Private function")
    parts.append(f"{missing_count} untested line{'s' if missing_count != 1 else ''}")
    if in_docs:
        parts.append(f"named in {doc_source}")
    return ", ".join(parts)


def _doc_source_label(func_name: str, project: Path) -> str:
    """Return 'README' or 'docs' or '' depending on where func_name is found."""
    search_name = func_name.split(".")[-1]
    pattern = re.compile(r"\b" + re.escape(search_name) + r"\b")

    readme = project / "README.md"
    if readme.exists():
        try:
            if pattern.search(readme.read_text(encoding="utf-8", errors="replace")):
                return "README"
        except OSError:
            pass

    docs_dir = project / "docs"
    if docs_dir.is_dir():
        for doc_path in docs_dir.rglob("*.md"):
            try:
                if pattern.search(doc_path.read_text(encoding="utf-8", errors="replace")):
                    return "docs"
            except OSError:
                continue
    return ""


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(project: str | Path, label: str = "before", src: str = "") -> int:
    """Parse coverage JSON, map missing lines to functions, write gaps.json.

    Args:
        project: Absolute path to the target project folder.
        label:   Coverage label to read (default ``"before"``).
        src:     Source subdirectory (for metadata only; used from metrics.json
                 when not supplied).

    Returns:
        0 always (gaps or no gaps).
    """
    project = Path(project).resolve()
    rdir = reports_dir()

    # --- load coverage JSON --------------------------------------------------
    cov_path = rdir / f"coverage_{label}.json"
    if not cov_path.exists():
        print(f"error: {cov_path} not found. Run 'testgap scan' first.")
        return 1

    cov_data = load_json(cov_path)
    totals = cov_data.get("totals", {})
    coverage_percent = round(float(totals.get("percent_covered", 0.0)), 1)
    files_data = cov_data.get("files", {})

    # --- resolve src from metrics if not provided ----------------------------
    if not src:
        metrics_path = rdir / "metrics.json"
        if metrics_path.exists():
            m = load_json(metrics_path)
            src = m.get("src", "")

    # --- iterate over files with missing lines --------------------------------
    # Group missing lines by function
    gap_map: dict[tuple[str, str], list[int]] = {}   # (rel_file, func_name) -> [lines]
    unattributed: list[int] = []

    for raw_file_key, file_info in files_data.items():
        missing_lines: list[int] = file_info.get("missing_lines", [])
        if not missing_lines:
            continue

        # Normalise path: replace backslashes, make relative to project
        norm_key = raw_file_key.replace("\\", "/")
        try:
            abs_file = (project / norm_key).resolve()
            rel_file = to_posix(abs_file.relative_to(project))
        except (ValueError, OSError):
            # If we can't resolve it, fall back to the normalised key
            rel_file = norm_key

        # Parse source with ast
        abs_path = project / rel_file.replace("/", "/")  # already posix
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Can't read — treat all lines as unattributed
            unattributed.extend(missing_lines)
            continue

        funcs = _collect_functions(source)

        for line in missing_lines:
            func = _innermost_function(line, funcs)
            if func is None:
                unattributed.append(line)
            else:
                key = (rel_file, func.name)
                gap_map.setdefault(key, [])
                if line not in gap_map[key]:
                    gap_map[key].append(line)

    # --- build gap records ---------------------------------------------------
    raw_gaps = []

    for (rel_file, func_name), missing in gap_map.items():
        missing_sorted = sorted(missing)
        is_pub = _is_public(func_name)
        in_docs = _mentioned_in_docs(func_name, project)
        doc_src = _doc_source_label(func_name, project) if in_docs else ""
        sc = score_gap(len(missing_sorted), is_pub, in_docs)
        pri = priority_label(sc)
        reason = _build_reason(func_name, len(missing_sorted), is_pub, in_docs, doc_src)

        # Recover start/end from ast for this file
        try:
            source = (project / rel_file).read_text(encoding="utf-8", errors="replace")
            funcs = _collect_functions(source)
        except OSError:
            funcs = []

        func_info = next((f for f in funcs if f.name == func_name), None)
        start_line = func_info.start_line if func_info else (missing_sorted[0] if missing_sorted else 0)
        end_line = func_info.end_line if func_info else (missing_sorted[-1] if missing_sorted else 0)

        raw_gaps.append({
            "file": rel_file,
            "function": func_name,
            "start_line": start_line,
            "end_line": end_line,
            "missing_lines": missing_sorted,
            "score": sc,
            "priority": pri,
            "reason": reason,
        })

    # --- sort: score desc, file asc, start_line asc --------------------------
    raw_gaps.sort(key=lambda g: (-g["score"], g["file"], g["start_line"]))

    # --- assign IDs after sorting --------------------------------------------
    for i, gap in enumerate(raw_gaps, start=1):
        gap["id"] = f"G-{i:03d}"

    # --- reorder keys to match Data Contract field order ---------------------
    gaps = [
        {
            "id": g["id"],
            "file": g["file"],
            "function": g["function"],
            "start_line": g["start_line"],
            "end_line": g["end_line"],
            "missing_lines": g["missing_lines"],
            "score": g["score"],
            "priority": g["priority"],
            "reason": g["reason"],
        }
        for g in raw_gaps
    ]

    # --- write gaps.json -----------------------------------------------------
    output = {
        "coverage_label": label,
        "coverage_percent": coverage_percent,
        "gaps": gaps,
        "project": project.name,
        "src": src,
        "unattributed_missing_lines": len(unattributed),
    }
    out_path = rdir / "gaps.json"
    save_json(out_path, output)

    # --- print summary -------------------------------------------------------
    if not gaps:
        print("Coverage is already high — no gaps found.")
        return 0

    high = sum(1 for g in gaps if g["priority"] == "high")
    medium = sum(1 for g in gaps if g["priority"] == "medium")
    low = sum(1 for g in gaps if g["priority"] == "low")
    print(f"{len(gaps)} gaps found ({high} high, {medium} medium, {low} low)")
    for gap in gaps[:3]:
        print(f"  {gap['id']} {gap['function']} ({gap['file']}) — score {gap['score']}")

    return 0
