#!/usr/bin/env python3
# Discover all Mesa example directories.

from pathlib import Path

MARKER_FILES = ("model.py", "run.py", "app.py")
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".github",
    "scripts",
    "files",
    "pulls",
    "node_modules",
}


def discover_all_examples(root="."):
    """Find all unique example directories."""
    examples = set()
    root_path = Path(root)

    for marker in MARKER_FILES:
        for p in root_path.rglob(marker):
            parent = p.parent
            if parent.name == parent.parent.name:
                parent = parent.parent
            if any(part in SKIP_DIRS or part.startswith(".") for part in parent.parts):
                continue
            examples.add(str(parent.relative_to(root_path)))

    # Keep only the outermost directory for each example
    result = sorted(examples)
    filtered = []
    for ex in result:
        if not any(ex.startswith(prev + "/") for prev in filtered):
            filtered.append(ex)
    return filtered


def find_example_root(filepath, repo_root="."):
    """Find the nearest example directory for a given file."""
    path = Path(filepath)
    repo = Path(repo_root)

    for parent in path.parents:
        if parent == repo or parent == Path("."):
            break
        if any(part in SKIP_DIRS or part.startswith(".") for part in parent.parts):
            break
        if any((parent / m).exists() for m in MARKER_FILES):
            return str(parent)
    return None
