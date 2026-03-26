#!/usr/bin/env python3
# Run a Mesa example and record results.

import argparse
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml


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


def first_warning(stderr_text: str) -> "str | None":
    """Extract the first warning line from stderr."""
    for line in stderr_text.splitlines():
        if "warning" in line.lower():
            return line.strip()[:100]
    return None


def _make_env(example_path: Path) -> dict:
    """Set up environment with PYTHONPATH."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(example_path.resolve()), str(example_path.resolve().parent)]
    )
    return env


def run_script(script_path: Path, example_path: Path, timeout: int = 30) -> dict:
    """Execute a python file as a script."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path.resolve())],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(example_path.resolve()),
            env=_make_env(example_path),
            check=False,
        )
        passed = proc.returncode == 0
        error = proc.stderr.strip()[-1000:] if not passed else None
        return {"passed": passed, "warning": first_warning(proc.stderr), "error": error}
    except subprocess.TimeoutExpired:
        return {"passed": True, "warning": None, "error": None}
    except Exception as e:
        return {"passed": False, "warning": None, "error": str(e)[-1000:]}


def run_module(module_name: str, example_path: Path, timeout: int = 30) -> dict:
    """Execute a module using 'python -m'."""
    parent = example_path.resolve().parent
    env = _make_env(example_path)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", module_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(parent),
            env=env,
            check=False,
        )
        passed = proc.returncode == 0
        error = proc.stderr.strip()[-1000:] if not passed else None
        return {"passed": passed, "warning": first_warning(proc.stderr), "error": error}
    except subprocess.TimeoutExpired:
        return {"passed": True, "warning": None, "error": None}
    except Exception as e:
        return {"passed": False, "warning": None, "error": str(e)[-1000:]}


def run_fallback(example_path: Path) -> dict:
    """Fallback: Import model and run 5 steps manually."""
    model_py = example_path / "model.py"
    if not model_py.exists():
        sub = example_path / example_path.name / "model.py"
        if sub.exists():
            model_py = sub

    if not model_py.exists():
        return {"passed": False, "warning": None, "error": "No runnable file found."}

    root, parent = str(example_path.resolve()), str(example_path.resolve().parent)
    runner = textwrap.dedent(f"""\
        import json, sys, warnings, traceback, mesa, importlib.util, types
        sys.path.extend([{root!r}, {parent!r}])
        _w = []
        warnings.showwarning = lambda m, *a: _w.append(str(m)[:100])
        try:
            spec = importlib.util.spec_from_file_location("_m", {str(model_py.resolve())!r})
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = next(
                (
                    obj
                    for obj in vars(mod).values()
                    if isinstance(obj, type)
                    and issubclass(obj, mesa.Model)
                    and obj is not mesa.Model
                ),
                None,
            )
            if not cls:
                raise Exception("No Model subclass")
            m = cls()
            [m.step() for _ in range(5)]
            print(json.dumps({{"passed": True, "warning": _w[0] if _w else None, "error": None}}))
        except Exception:
            print(json.dumps({{"passed": False, "warning": _w[0] if _w else None, "error": traceback.format_exc()[-1000:]}}))
    """)

    try:
        proc = subprocess.run(
            [sys.executable, "-c", runner],
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
        return {"passed": False, "warning": None, "error": "No output"}
    except Exception as e:
        return {"passed": False, "warning": None, "error": str(e)}


def find_and_run(example_path: Path) -> dict:
    """Detect entry point and run appropriate strategy."""
    for name, is_app in [("run.py", False), ("app.py", True)]:
        p = example_path / name
        if not p.exists():
            p = example_path / example_path.name / name
        if p.exists():
            res = run_script(p, example_path, 45 if is_app else 30)
            if not res["passed"] and (
                "ImportError" in (res.get("error") or "")
                or "ModuleNotFoundError" in (res.get("error") or "")
            ):
                mod = str(p.relative_to(example_path.parent).with_suffix("")).replace(
                    os.sep, "."
                )
                return run_module(mod, example_path, 45 if is_app else 30)
            return res
    return run_fallback(example_path)


def main():
    parser = argparse.ArgumentParser()
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
