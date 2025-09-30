"""Onboarding helper for new contributors.

Runs minimal setup and a dry-run generation so new contributors can see
what artifacts the project produces. Prints locations of generated files.

Lightweight: uses existing Makefile targets and requires no extra deps.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: str) -> None:
    print(f"$ {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(res.returncode)


def main() -> None:
    # Run setup and a single-week dry run to produce .out/week-1 artifacts
    run("make setup")
    # Use the Makefile's dry-run target (week=1)
    run("make dry-run week=1")

    out = Path(".out") / "week-1"
    print("\nOnboarding artifacts (if present):")
    if not out.exists():
        print("  - No artifacts found under .out/week-1")
        print("  - If make dry-run failed, inspect previous output above for errors.")
        return

    print(f"  - Manifest JSON: {out / 'manifest.json'}")
    print(f"  - Manifest CSV:  {out / 'manifest.csv'}")
    print(f"  - Sample script(s): {next(out.glob('*.md'), 'none')}")
    print(f"  - Audit logs (skipped approvals): {out / 'audit' / 'skipped.log'}")


if __name__ == '__main__':
    main()
