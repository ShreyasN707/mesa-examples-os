#!/usr/bin/env python3
# Update per-example registry files from test results.

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Fix path to allow importing from discovery
sys.path.append(str(Path(__file__).parent.parent))
from discovery.discover_examples import discover_all_examples


def _find_readme(example_path: Path) -> Path | None:
    """Find README regardless of casing."""
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


def compute_health(results: dict) -> tuple:
    """Calculate example health based on stable and main results."""
    stable, main = results.get("stable"), results.get("main")
    warn = next(
        (r["warning"] for r in results.values() if r and r.get("warning")), None
    )

    if not stable or stable.get("skipped"):
        return "untested", None
    if not stable.get("passed"):
        return "broken", warn

    main_failed = main and not main.get("skipped") and not main.get("passed")
    if main_failed or warn:
        return "warning", warn

    return "passing", None


def load_results(results_dir: Path) -> dict:
    """Load all JSON results and group by example ID."""
    grouped = {}
    for result_file in results_dir.rglob("*.json"):
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            example_id, version = data.get("example_id"), data.get("version")
            if example_id and version:
                grouped.setdefault(example_id, {})[version] = data
        except (json.JSONDecodeError, OSError):
            continue
    return grouped


def build_record(example_id: str, example_path: Path, results: dict) -> dict:
    """Build a complete registry record for an example."""
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
    """Check if record changed significantly (ignores last_run date)."""

    def clean(r):
        c = r.copy()
        c["ci"] = {k: v for k, v in c.get("ci", {}).items() if k != "last_run"}
        return c

    return clean(old) != clean(new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--registry-dir", default="registry")
    parser.add_argument("--search-root", default=".")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    registry_dir = Path(args.registry_dir)
    search_root = Path(args.search_root)
    registry_dir.mkdir(parents=True, exist_ok=True)
    all_results = load_results(results_dir)

    for ex_id in discover_all_examples(root=search_root):
        new_record = build_record(
            ex_id, search_root / ex_id, all_results.get(ex_id, {})
        )
        safe_name = ex_id.replace("/", "_").replace("\\", "_")
        reg_file = registry_dir / f"{safe_name}.json"

        if reg_file.exists():
            try:
                old = json.loads(reg_file.read_text(encoding="utf-8"))
                if not meaningful_change(old, new_record):
                    continue
            except (json.JSONDecodeError, OSError):
                pass

        reg_file.write_text(json.dumps(new_record, indent=2), encoding="utf-8")
        print(f"  updated    {ex_id}")


if __name__ == "__main__":
    main()
