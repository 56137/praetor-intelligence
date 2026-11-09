#!/usr/bin/env python3
"""Create a private, empty local PRAETOR prospect file."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _is_ignored_by_git(path: Path, repo_root: Path) -> bool:
    """Fail closed for repository-local output unless Git ignores the path."""
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return True  # Outside the repository.

    git = shutil.which("git")
    if not git or not (root / ".git").exists():
        return False

    result = subprocess.run(
        [git, "check-ignore", "--quiet", "--", relative.as_posix()],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _write_json_exclusive(path: Path, payload: dict) -> None:
    """Write privately to a same-directory temp file, then publish atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        # Publish atomically without overwriting a file created concurrently.
        os.link(temp_path, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an empty private PRAETOR prospect-list template."
    )
    parser.add_argument(
        "--output",
        default="prospectos_ensenada.json",
        help="Local output path (default: prospectos_ensenada.json).",
    )
    parser.add_argument(
        "--city",
        default="Ensenada, Baja California",
        help="Label for the prospect list.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    repo_root = Path(__file__).resolve().parent

    if not _is_ignored_by_git(output_path, repo_root):
        parser.error(
            f"{output_path} is inside the repository and is not Git-ignored. "
            "Choose a private path outside the repository or add a suitable "
            ".gitignore rule first."
        )

    payload = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ciudad": args.city,
        "prospectos": [],
    }

    try:
        _write_json_exclusive(output_path, payload)
    except FileExistsError:
        parser.error(
            f"{output_path} already exists; refusing to overwrite private data."
        )

    print(f"Empty private prospect template created: {output_path}")
    print("Add authorized contact records locally; do not commit this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
