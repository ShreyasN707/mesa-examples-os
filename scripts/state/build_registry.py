#!/usr/bin/env python3
"""Update per-example registry files from validation results."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Directories to skip when scanning for examples
_SKIP = {".git", "__pycache__", ".github", "scripts", "files", "pulls", "node_modules"}
_MARKERS = ("model.py", "run.py", "app.py")


# ---------------------------------------------------------------------------
# Example scanning (replaces discovery module)
# ---------------------------------------------------------------------------


def scan_examples(root="."):
    """Find all example directories containing a Mesa marker file."""
    root_path = Path(root)
    examples = set()

    for marker in _MARKERS:
        for p in root_path.rglob(marker):
            parent = p.parent
            # If the example has a nested package dir with same name, go up
            if parent.name == parent.parent.name:
                parent = parent.parent
            if any(part in _SKIP or part.startswith(".") for part in parent.parts):
                continue
            examples.add(str(parent.relative_to(root_path)))

    # Keep only outermost directories
    result = sorted(examples)
    return [
        ex
        for ex in result
        if not any(ex.startswith(o + "/") for o in result if o != ex)
    ]


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _find_readme(example_path: Path) -> Path | None:
    if not example_path.is_dir():
        return None
    for f in example_path.iterdir():
        if f.is_file() and f.name.lower() == "readme.md":
            return f
    return None


def parse_frontmatter(example_path: Path) -> dict:
    """Parse YAML frontmatter from README."""
    readme = _find_readme(example_path)
    if not readme:
        return {}
    text = readme.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    close = text.find("\n---", 3)
    if close == -1:
        return {}
    try:
        return yaml.safe_load(text[3:close]) or {}
    except yaml.YAMLError:
        return {}


# ---------------------------------------------------------------------------
# Health computation
# ---------------------------------------------------------------------------


def compute_health(results: dict) -> tuple:
    """Calculate health from stable/main results."""
    stable = results.get("stable")
    main = results.get("main")
    warn = next(
        (r["warning"] for r in results.values() if r and r.get("warning")), None
    )

    if not stable or stable.get("skipped"):
        return "untested", None
    if not stable.get("passed"):
        return "broken", warn
    if (main and not main.get("skipped") and not main.get("passed")) or warn:
        return "warning", warn
    return "passing", None


# ---------------------------------------------------------------------------
# Registry building
# ---------------------------------------------------------------------------


def load_results(results_dir: Path) -> dict:
    """Load JSON results and group by example ID."""
    grouped = {}
    for f in results_dir.rglob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            eid, ver = data.get("example_id"), data.get("version")
            if eid and ver:
                grouped.setdefault(eid, {})[ver] = data
        except (json.JSONDecodeError, OSError):
            continue
    return grouped


def build_record(example_id: str, example_path: Path, results: dict) -> dict:
    """Build a complete registry record."""
    meta = parse_frontmatter(example_path)
    health, warning = compute_health(results)

    compat = {
        v: (
            "untested"
            if not results.get(v) or results[v].get("skipped")
            else ("pass" if results[v].get("passed") else "fail")
        )
        for v in ("stable", "main", "rc")
    }

    return {
        "location": example_id,
        "name": meta.get("title", example_id),
        "meta": {
            "status": meta.get("status", "incubator"),
            "complexity": meta.get("complexity", "beginner"),
        },
        "ci": {
            "health": health,
            "warning": warning,
            "last_run": datetime.now(timezone.utc).date().isoformat(),
        },
        "compatibility": compat,
    }


def meaningful_change(old: dict, new: dict) -> bool:
    """True if record changed (ignoring last_run date)."""

    def clean(r):
        c = r.copy()
        c["ci"] = {k: v for k, v in c.get("ci", {}).items() if k != "last_run"}
        return c

    return clean(old) != clean(new)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build registry from validation results."
    )
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--registry-dir", default="registry")
    parser.add_argument("--search-root", default=".")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    registry_dir = Path(args.registry_dir)
    search_root = Path(args.search_root)
    registry_dir.mkdir(parents=True, exist_ok=True)

    all_results = load_results(results_dir)

    for ex_id in scan_examples(root=search_root):
        record = build_record(ex_id, search_root / ex_id, all_results.get(ex_id, {}))
        safe_name = ex_id.replace("/", "_").replace("\\", "_")
        reg_file = registry_dir / f"{safe_name}.json"

        if reg_file.exists():
            try:
                old = json.loads(reg_file.read_text(encoding="utf-8"))
                if not meaningful_change(old, record):
                    continue
            except (json.JSONDecodeError, OSError):
                pass

        reg_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"  updated    {ex_id}")


if __name__ == "__main__":
    main()
