"""`karaoke-server`: run the server and look after it."""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from karaoke_server.config import REPO, Settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="karaoke-server", description=__doc__)
    parser.add_argument("--data", type=Path, help="data folder (default: ~/.local/share/karaoke)")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="run the server")
    serve.add_argument("--port", type=int, help="home port (the tunnel port is the next one)")
    serve.add_argument(
        "--open-home",
        action="store_true",
        help="let anyone on the home network create, edit and delete",
    )
    serve.add_argument("--fake-engine", action="store_true", help="pretend to make karaokes")
    serve.add_argument("--web", type=Path, help="built web app (default: web/build)")
    serve.add_argument("--verbose", action="store_true")
    commands.add_parser("pair", help="a code to pair a phone or another computer")
    devices = commands.add_parser("devices", help="list paired devices")
    devices.add_argument("--revoke", metavar="ID", help="unpair a device")
    imported = commands.add_parser("import", help="copy karaoke packages into the library")
    imported.add_argument("packages", type=Path, nargs="+")
    copies = commands.add_parser("backup", help="copy the library somewhere safe")
    copies.add_argument("--to", type=Path, help="destination (default: KARAOKE_BACKUP_DIR)")
    prepare = commands.add_parser("prepare", help="download the models before the first song")
    prepare.add_argument("--lang", default="gl")
    openapi = commands.add_parser("openapi", help="write the API description (OpenAPI)")
    openapi.add_argument("--out", type=Path, default=REPO / "schemas" / "openapi.json")
    commands.add_parser("doctor", help="check that everything is in place")
    start = commands.add_parser("autostart", help="start the server with Windows")
    start.add_argument("action", choices=["install", "remove", "status"])
    args = parser.parse_args(argv)

    overrides = {"data_dir": args.data}
    if args.command == "serve":
        overrides.update(
            home_port=args.port,
            web_dir=args.web,
            open_home=args.open_home or None,
            fake_engine=args.fake_engine or None,
        )
    settings = Settings.from_env(**overrides)
    handler = {
        "serve": _serve,
        "pair": _pair,
        "devices": _devices,
        "import": _import,
        "backup": _backup,
        "prepare": _prepare,
        "openapi": _openapi,
        "doctor": _doctor,
        "autostart": _autostart,
    }[args.command]
    return handler(settings, args)


def _serve(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server.serve import serve

    serve(settings, verbose=args.verbose)
    return 0


def _database(settings: Settings):  # type: ignore[no-untyped-def]
    from karaoke_server.db import Database

    settings.ensure_dirs()
    db = Database(settings.db_path)
    db.migrate()
    return db


def _pair(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server import network
    from karaoke_server.access import Devices

    pairing = Devices(_database(settings)).start_pairing()
    # Another process than the server: it looks the addresses up itself (a few seconds).
    info = network.Network(settings, network.probe_network()).info()
    links = [info.home_url if info.home_reachable else None, info.remote_url]
    expires = datetime.fromtimestamp(pairing.expires_at, UTC).astimezone().strftime("%H:%M")
    print(f"Pairing code: {pairing.code}  (valid until {expires}, once)")
    if any(links):
        print("On the phone, open Axustes and type it in, or open:")
    else:
        print("On the phone, open Axustes and type it in.")
    for base in links:
        if base:
            print(f"  {base}/vincular?code={pairing.code}")
    return 0


def _devices(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server.access import Devices

    devices = Devices(_database(settings))
    if args.revoke:
        if not devices.revoke(args.revoke):
            print(f"No device {args.revoke}", file=sys.stderr)
            return 1
        print(f"Unpaired {args.revoke}")
        return 0
    found = devices.list()
    for device in found:
        seen = f"paired {device.created_at}, last seen {device.last_seen}"
        print(f"{device.id}  {device.name:<28}  {seen}")
    if not found:
        print("No paired devices yet (karaoke-server pair)")
    return 0


def _import(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server.library import InvalidDocError, Library

    library = Library(settings, _database(settings))
    failed = 0
    for package in args.packages:
        try:
            print(f"{package}: imported as {library.import_package(package)}")
        except (InvalidDocError, OSError) as exc:
            print(f"{package}: not imported: {exc}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


def _backup(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server.backup import backup

    dest = args.to or settings.backup_dir
    if dest is None:
        print(
            "Say where: karaoke-server backup --to <folder> (or set KARAOKE_BACKUP_DIR)",
            file=sys.stderr,
        )
        return 2
    report = backup(settings, _database(settings), dest)
    print(
        f"{dest}: {report.copied} files copied ({report.bytes / 1024**2:.0f} MB), "
        f"{report.skipped} unchanged, {report.removed} set aside"
    )
    return 0


def _prepare(settings: Settings, args: argparse.Namespace) -> int:
    import subprocess

    spec = settings.tmp_dir / "prepare.json"
    settings.ensure_dirs()
    spec.write_text(json.dumps({"kind": "prepare", "language": args.lang}), encoding="utf-8")
    # In a process of its own: converting a model takes most of the memory for a while.
    return subprocess.run(
        [sys.executable, "-m", "karaoke_server.jobs.runner", str(spec)]
    ).returncode


def _openapi(settings: Settings, args: argparse.Namespace) -> int:
    import tempfile

    from karaoke_server.app import build_services, create_app
    from karaoke_server.network import NetworkState

    # The description does not depend on any data: a scratch folder keeps the real one untouched.
    with tempfile.TemporaryDirectory() as scratch:
        scratch_settings = Settings.from_env(data_dir=Path(scratch))
        services = build_services(
            scratch_settings,
            network_state=NetworkState(None, None, None, None),
            gateways=frozenset(),
        )
        schema = create_app(scratch_settings, services=services).openapi()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Written {args.out}")
    return 0


def _doctor(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server.doctor import render, run_checks

    checks = run_checks(settings)
    print(render(checks))
    return 0 if all(c.ok or c.optional for c in checks) else 1


def _autostart(settings: Settings, args: argparse.Namespace) -> int:
    from karaoke_server import autostart

    if args.action == "install":
        print(f"Installed: {autostart.install(REPO)}")
        print("The server will start when you log in to Windows.")
    elif args.action == "remove":
        print("Removed" if autostart.remove() else "It was not installed")
    else:
        path = autostart.status()
        print(f"Installed: {path}" if path else "Not installed (karaoke-server autostart install)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
