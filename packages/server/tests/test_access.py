from pathlib import Path

import pytest

from karaoke_server.access import (
    Devices,
    PairingLockedError,
    classify,
    device_name,
    wsl_gateways,
)
from karaoke_server.config import Settings
from karaoke_server.db import Database

NO_GATEWAYS: frozenset[str] = frozenset()


SETTINGS = Settings.from_env(data_dir=Path("/x"))


def zone(
    host: str | None,
    port: int = 8765,
    headers: dict[str, str] | None = None,
    gateways: frozenset[str] = NO_GATEWAYS,
) -> str:
    return classify(host, port, headers or {}, SETTINGS, gateways)


def test_loopback_is_local() -> None:
    assert zone("127.0.0.1") == "local"
    assert zone("::1") == "local"


@pytest.mark.parametrize(
    ("client", "host"),
    [
        ("127.0.0.1", "localhost:8765"),
        ("127.0.0.1", "127.0.0.1:8765"),
        ("127.0.0.1", "karaoke.localhost:8765"),
        ("::1", "[::1]:8765"),
        ("127.0.0.1", "LOCALHOST"),
    ],
)
def test_the_laptop_is_local_by_its_loopback_names(client: str, host: str) -> None:
    assert zone(client, headers={"host": host}) == "local"


def test_a_page_rebound_to_loopback_is_not_the_laptop() -> None:
    # DNS rebinding: a site whose name now points at 127.0.0.1, in the laptop's own browser.
    assert zone("127.0.0.1", headers={"host": "evil.example:8765"}) == "remote"
    assert zone("127.0.0.1", headers={"host": "192.168.1.38:8765"}) == "remote"


def test_tunnel_port_is_remote_even_from_loopback() -> None:
    assert zone("127.0.0.1", port=8766) == "remote"


@pytest.mark.parametrize(
    "header",
    [
        "x-forwarded-for",
        "forwarded",
        "x-real-ip",
        "cf-connecting-ip",
        "tailscale-user-login",
        "tailscale-funnel-request",
    ],
)
def test_forwarded_headers_make_a_request_remote(header: str) -> None:
    assert zone("127.0.0.1", headers={header: "1.2.3.4"}) == "remote"
    assert zone("192.168.1.20", headers={header: "1.2.3.4"}) == "remote"


@pytest.mark.parametrize(
    "host",
    [
        "192.168.1.20",
        "10.0.0.7",
        "172.20.1.1",
        "169.254.3.4",
        "fd12::1",
        "fe80::1",
        "::ffff:192.168.1.9",
    ],
)
def test_private_lan_is_home(host: str) -> None:
    assert zone(host) == "home"


def test_wsl_gateway_is_remote() -> None:
    assert zone("172.24.144.1", gateways=frozenset({"172.24.144.1"})) == "remote"


@pytest.mark.parametrize("host", ["100.85.232.61", "8.8.8.8", "2001:db8::1", None, "testclient"])
def test_tailscale_cgnat_and_public_are_remote(host: str | None) -> None:
    assert zone(host) == "remote"


def test_wsl_gateways_only_in_nat_mode(tmp_path: Path) -> None:
    route = tmp_path / "route"
    route.write_text(
        "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\n"
        "eth0\t00000000\t019018AC\t0003\t0\t0\t0\t00000000\n"
        "eth0\t009018AC\t00000000\t0001\t0\t0\t0\t00F0FFFF\n"
    )
    assert wsl_gateways(lambda: "nat", route) == frozenset({"172.24.144.1"})
    assert wsl_gateways(lambda: "mirrored", route) == frozenset()
    assert wsl_gateways(lambda: None, route) == frozenset()


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def devices(db: Database, clock: Clock) -> Devices:
    return Devices(db, now=clock)


def test_pairing_code_shape(devices: Devices) -> None:
    pairing = devices.start_pairing()
    assert len(pairing.code) == 8
    assert set(pairing.code) <= set("BCDFGHJKLMNPQRSTVWXZ")


def test_pairing_code_is_single_use(devices: Devices) -> None:
    code = devices.start_pairing().code
    paired = devices.pair(code.lower(), "iPhone · Safari")
    assert paired is not None
    device, token = paired
    assert device.name == "iPhone · Safari"
    assert devices.verify(token) == device
    assert devices.pair(code, "again") is None


def test_pairing_code_accepts_spaces_and_dashes(devices: Devices) -> None:
    code = devices.start_pairing().code
    assert devices.pair(f" {code[:4]}-{code[4:]} ", "x") is not None


def test_pairing_code_expires_after_ten_minutes(devices: Devices, clock: Clock) -> None:
    code = devices.start_pairing().code
    clock.t += 601
    assert devices.pair(code, "late") is None


def test_pairing_locks_after_ten_failures(devices: Devices, clock: Clock) -> None:
    code = devices.start_pairing().code
    for _ in range(10):
        assert devices.pair("BBBBBBBB", "guess") is None
    with pytest.raises(PairingLockedError):
        devices.pair(code, "owner")
    clock.t += 601
    assert devices.pair(devices.start_pairing().code, "owner") is not None


def test_tokens_are_stored_hashed(devices: Devices, db: Database) -> None:
    _, token = devices.pair(devices.start_pairing().code, "x")  # type: ignore[misc]
    stored = db.query("SELECT token_hash FROM devices")[0]["token_hash"]
    assert token not in stored
    assert len(stored) == 64


def test_revoked_device_is_no_longer_known(devices: Devices) -> None:
    device, token = devices.pair(devices.start_pairing().code, "x")  # type: ignore[misc]
    assert [d.id for d in devices.list()] == [device.id]
    assert devices.revoke(device.id) is True
    assert devices.verify(token) is None
    assert devices.revoke(device.id) is False


def test_unknown_token_is_nobody(devices: Devices) -> None:
    assert devices.verify("") is None
    assert devices.verify("nonsense") is None


@pytest.mark.parametrize(
    ("agent", "name"),
    [
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
            "iPhone · Safari",
        ),
        (
            "Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Mobile Safari/537.36",
            "Android · Chrome",
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36 Edg/140.0",
            "Windows · Edge",
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0; rv:140.0) Gecko/20100101 Firefox/140.0",
            "Mac · Firefox",
        ),
        ("", "Device"),
    ],
)
def test_device_name_from_user_agent(agent: str, name: str) -> None:
    assert device_name(agent) == name


def test_a_code_made_by_another_process_works(db: Database, clock: Clock) -> None:
    code = Devices(db, now=clock).start_pairing().code
    assert Devices(db, now=clock).pair(code, "phone") is not None
