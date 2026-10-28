"""The `karaoke` command. Later conversations add `make` (engine) and `render` (video)."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from karaoke_contracts import validate_file, validate_package
from karaoke_engine.demo import synthesize_package_audio


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="karaoke", description="Karaoke generator tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate", help="check a karaoke package folder (or just its karaoke.json)"
    )
    validate.add_argument("path", type=Path)

    demo = commands.add_parser(
        "demo", help="write synthetic audio for a package that follows its lyric timings"
    )
    demo.add_argument("package", type=Path)

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate(args.path)
    try:
        synthesize_package_audio(args.package)
    except (OSError, ValueError) as exc:  # ValueError covers pydantic's ValidationError
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Synthetic audio written to {args.package}")
    return 0


def _validate(path: Path) -> int:
    issues = validate_package(path) if path.is_dir() else validate_file(path)
    for issue in issues:
        print(f"{issue.path}: {issue.message}")
    if issues:
        return 1
    print("OK")
    return 0
