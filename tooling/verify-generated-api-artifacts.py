from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKED_FILES = [
    "packages/api-spec/openapi.json",
    "apps/harvester-dashboard/types/api.generated.ts",
    "apps/mobile/types/api.generated.ts",
]


def run_command(args: list[str]) -> None:
    """Run a command in the repo root and raise on failure."""
    subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def run_git(args: list[str]) -> str:
    """Run git in the repo root and return stdout as text."""
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def main() -> int:
    try:
        run_command(["node", str(ROOT / "tooling" / "generate-frontend-types.mjs")])
    except subprocess.CalledProcessError as error:
        return error.returncode or 1

    try:
        run_git(["diff", "--exit-code", "--", *TRACKED_FILES])
    except subprocess.CalledProcessError as error:
        print("Generated API artifacts drifted from the committed versions.", file=sys.stderr)
        try:
            changed_files = run_git(["diff", "--name-only", "--", *TRACKED_FILES]).strip()
            if changed_files:
                print(changed_files, file=sys.stderr)
        except subprocess.CalledProcessError:
            pass
        return error.returncode or 1

    print("Generated API artifacts are up to date.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
