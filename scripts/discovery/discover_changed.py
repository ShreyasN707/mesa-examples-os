#!/usr/bin/env python3
# Detect changed examples in a PR.

import json
import subprocess
import sys
from pathlib import Path

# Fix path to allow importing from discovery
sys.path.append(str(Path(__file__).resolve().parent.parent))
from discovery.discover_examples import find_example_root


def main():
    if len(sys.argv) < 3:
        print("Usage: discover_changed.py <base_ref> <head_ref>")
        sys.exit(1)

    base_ref, head_ref = sys.argv[1], sys.argv[2]
    cmd = ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        print(json.dumps(["ALL"]))
        sys.exit(0)

    changed_files = proc.stdout.splitlines()
    affected_examples = set()
    shared_changed = False

    for f in changed_files:
        # Ignore root-level documentation
        if f.endswith(".md") and "/" not in f:
            continue
        root = find_example_root(f)
        if root:
            affected_examples.add(root)
        else:
            shared_changed = True

    # If shared infra changed, test everything
    if shared_changed:
        print(json.dumps(["ALL"]))
    else:
        print(json.dumps(sorted(affected_examples)))


if __name__ == "__main__":
    main()
