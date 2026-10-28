"""The `karaoke` command. Later conversations add `make` (engine) and `render` (video)."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from karaoke_contracts import Issue, load_doc, validate_doc, validate_package
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
    synthesize_package_audio(args.package)
    print(f"Synthetic audio written to {args.package}")
    return 0


def _validate(path: Path) -> int:
    if path.is_dir():
        issues = validate_package(path)
    else:
        try:
            issues = validate_doc(load_doc(path))
        except ValidationError as exc:
            issues = [Issue(".".join(map(str, e["loc"])), e["msg"]) for e in exc.errors()]
    for issue in issues:
        print(f"{issue.path}: {issue.message}")
    if issues:
        return 1
    print("OK")
    return 0
