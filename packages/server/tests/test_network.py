import json
from pathlib import Path

from karaoke_server.config import Settings
from karaoke_server.network import (
    Network,
    NetworkState,
    pick_home_ip,
    serve_target_port,
    tailscale_host,
)


def test_pick_home_ip_prefers_the_wifi_address() -> None:
    lines = [
        "1: lo    inet 127.0.0.1/8 scope host lo",
        "2: eth0    inet 172.24.152.63/20 brd 172.24.159.255 scope global eth0",
        "3: eth1    inet 192.168.1.43/24 brd 192.168.1.255 scope global eth1",
        "4: eth2    inet 100.85.232.61/32 scope global eth2",
        "5: eth3    inet 169.254.3.4/16 scope link eth3",
    ]
    assert pick_home_ip("\n".join(lines)) == "192.168.1.43"
    assert pick_home_ip("") is None


def test_tailscale_host_from_status() -> None:
    status = {"Self": {"DNSName": "gaelb.tailaf8c79.ts.net."}, "BackendState": "Running"}
    assert tailscale_host(json.dumps(status)) == "gaelb.tailaf8c79.ts.net"
    assert tailscale_host(json.dumps({"BackendState": "Stopped", "Self": {}})) is None
    assert tailscale_host("not json") is None


def test_serve_target_port() -> None:
    handlers = {"/": {"Proxy": "http://127.0.0.1:8766"}}
    serve = {"TCP": {"443": {"HTTPS": True}}, "Web": {"g.ts.net:443": {"Handlers": handlers}}}
    assert serve_target_port(json.dumps(serve)) == 8766
    assert serve_target_port("{}") is None


def test_network_info_in_nat_and_mirrored(tmp_path: Path) -> None:
    settings = Settings.from_env(data_dir=tmp_path)
    mirrored = Network(settings, NetworkState("mirrored", "192.168.1.43", "gaelb.t.ts.net", 8766))
    info = mirrored.info()
    assert info.url == "http://192.168.1.43:8765"
    assert info.home_reachable is True
    assert info.remote_url == "https://gaelb.t.ts.net"
    nat = Network(settings, NetworkState("nat", "192.168.1.43", "gaelb.t.ts.net", None)).info()
    assert nat.home_reachable is False
    assert nat.remote_url is None
    nothing = Network(settings, NetworkState(None, None, None, None)).info()
    assert nothing.url == "http://localhost:8765"
