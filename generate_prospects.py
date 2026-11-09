#!/usr/bin/env python3
"""Initialize an empty local prospect file without embedding customer data."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an empty local PRAETOR prospect-list template."
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
    if output_path.exists():
        parser.error(
            f"{output_path} already exists; refusing to overwrite private data."
        )

    payload = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": 0,
        "ciudad": args.city,
        "prospectos": [],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Empty private prospect template created: {output_path}")
    print("Add authorized contact records locally; do not commit this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
