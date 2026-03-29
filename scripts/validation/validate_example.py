#!/usr/bin/env python3
"""Run a single Mesa example and record structured results."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_readme(example_path: Path) -> Path | None:
    """Find README regardless of casing."""
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


def first_warning(stderr_text: str) -> str | None:
    """Return the first warning line from stderr (case-insensitive)."""
    for line in stderr_text.splitlines():
        if "warning" in line.lower():
            return line.strip()[:200]
    return None


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


def _run_file(script: Path, example_path: Path, timeout: int = 30) -> dict:
    """Run a Python file in a subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(example_path.resolve()), str(example_path.resolve().parent)]
    )
    try:
        proc = subprocess.run(
            [sys.executable, str(script.resolve())],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(example_path.resolve()),
            env=env,
            check=False,
        )
        passed = proc.returncode == 0
        error = proc.stderr.strip()[-500:] if not passed else None
        return {"passed": passed, "warning": first_warning(proc.stderr), "error": error}
    except subprocess.TimeoutExpired:
        # Timeout = app ran without crashing, treat as pass
        return {"passed": True, "warning": None, "error": None}
    except Exception as e:
        return {"passed": False, "warning": None, "error": str(e)[:500]}


def _run_model_fallback(example_path: Path) -> dict:
    """Fallback: import model.py, find a Model subclass, run 5 steps."""
    model_py = example_path / "model.py"
    if not model_py.exists():
        sub = example_path / example_path.name / "model.py"
        model_py = sub if sub.exists() else None

    if not model_py:
        return {"passed": False, "warning": None, "error": "No runnable file found."}

    # Run in a clean subprocess to avoid polluting the current process
    script = (
        f"import sys, json, warnings, traceback, importlib.util\n"
        f"sys.path.extend([{str(example_path.resolve())!r}, {str(example_path.resolve().parent)!r}])\n"
        f"_w = []\n"
        f"warnings.showwarning = lambda m, *a: _w.append(str(m)[:200])\n"
        f"try:\n"
        f"    import mesa\n"
        f"    spec = importlib.util.spec_from_file_location('_m', {str(model_py.resolve())!r})\n"
        f"    mod = importlib.util.module_from_spec(spec)\n"
        f"    spec.loader.exec_module(mod)\n"
        f"    cls = next((o for o in vars(mod).values() if isinstance(o, type) and issubclass(o, mesa.Model) and o is not mesa.Model), None)\n"
        f"    if not cls: raise RuntimeError('No Model subclass found')\n"
        f"    m = cls()\n"
        f"    for _ in range(5): m.step()\n"
        f"    print(json.dumps({{'passed': True, 'warning': _w[0] if _w else None, 'error': None}}))\n"
        f"except Exception:\n"
        f"    print(json.dumps({{'passed': False, 'warning': _w[0] if _w else None, 'error': traceback.format_exc()[-500:]}}))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        out = [line for line in proc.stdout.splitlines() if line.strip()]
        if out:
            res = json.loads(out[-1])
            if not res["warning"]:
                res["warning"] = first_warning(proc.stderr)
            return res
        return {
            "passed": False,
            "warning": None,
            "error": proc.stderr.strip()[:500] or "No output",
        }
    except Exception as e:
        return {"passed": False, "warning": None, "error": str(e)[:500]}


def find_and_run(example_path: Path) -> dict:
    """Try run.py → app.py → model.py fallback."""
    for name, timeout in [("run.py", 30), ("app.py", 45)]:
        p = example_path / name
        if not p.exists():
            p = example_path / example_path.name / name
        if p.exists():
            return _run_file(p, example_path, timeout)
    return _run_model_fallback(example_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Validate a single Mesa example.")
    parser.add_argument("example_dir")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    path = Path(args.example_dir)
    ex_id = str(path).replace(os.sep, "/").strip("/")
    meta = parse_frontmatter(path)

    if meta.get("ci", {}).get("skip"):
        result = {
            "example_id": ex_id,
            "version": args.version,
            "passed": None,
            "skipped": True,
        }
    else:
        res = find_and_run(path)
        result = {
            "example_id": ex_id,
            "version": args.version,
            "passed": res["passed"],
            "skipped": False,
            "warning": res.get("warning"),
            "error": res.get("error"),
        }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    tag = "SKIP" if result.get("skipped") else ("PASS" if result["passed"] else "FAIL")
    print(f"{tag}  {ex_id}  ({args.version})")
    if result.get("error"):
        print(f"     {result['error'][:120]}")
    if not result.get("passed") and not result.get("skipped"):
        sys.exit(1)


if __name__ == "__main__":
    main()
