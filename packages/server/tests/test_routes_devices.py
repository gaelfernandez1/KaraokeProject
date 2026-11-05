from karaoke_server.access import COOKIE
from karaoke_server.config import Settings

from .conftest import MakeClient


def test_me_reports_zone_and_owner(make_client: MakeClient) -> None:
    assert make_client("local").get("/api/me").json() == {
        "owner": True,
        "zone": "local",
        "device": None,
    }
    assert make_client("home").get("/api/me").json()["owner"] is False
    assert make_client("remote").get("/api/me").json()["zone"] == "remote"


def test_pairing_flow_sets_a_cookie_that_makes_an_owner(
    make_client: MakeClient, settings: Settings
) -> None:
    local = make_client("local")
    assert make_client("home").post("/api/devices/pairing").status_code == 403
    pairing = local.post("/api/devices/pairing").json()
    assert len(pairing["code"]) == 8
    assert (
        pairing["urls"]["home"]
        == f"http://192.168.1.20:{settings.home_port}/vincular?code={pairing['code']}"
    )
    phone = make_client("remote", headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari/604.1"})
    assert phone.get("/api/songs").status_code == 403
    paired = phone.post("/api/devices/pair", json={"code": pairing["code"]})
    assert paired.status_code == 200
    assert paired.json()["name"] == "iPhone · Safari"
    cookie = paired.headers["set-cookie"]
    assert COOKIE in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie or "SameSite=Lax" in cookie
    assert "Secure" not in cookie
    assert phone.get("/api/songs").status_code == 200
    me = phone.get("/api/me").json()
    assert me["owner"] is True
    assert me["device"]["name"] == "iPhone · Safari"
    devices = local.get("/api/devices").json()
    assert [d["name"] for d in devices] == ["iPhone · Safari"]
    assert local.delete(f"/api/devices/{devices[0]['id']}").status_code == 204
    assert phone.get("/api/songs").status_code == 403


def test_wrong_code_and_lockout(make_client: MakeClient) -> None:
    phone = make_client("remote")
    for _ in range(10):
        wrong = phone.post("/api/devices/pair", json={"code": "BBBBBBBB"})
        assert wrong.status_code == 422
        assert wrong.json()["code"] == "bad_code"
    assert phone.post("/api/devices/pair", json={"code": "BBBBBBBB"}).status_code == 429


def test_cookie_is_secure_over_https(make_client: MakeClient) -> None:
    code = make_client("local").post("/api/devices/pairing").json()["code"]
    tunnel = make_client("local", base_url="https://gaelb.example.ts.net:8766")
    paired = tunnel.post("/api/devices/pair", json={"code": code})
    assert paired.status_code == 200
    assert "Secure" in paired.headers["set-cookie"]


def test_pair_through_a_proxy_keeps_the_forwarded_host(make_client: MakeClient) -> None:
    code = make_client("local").post("/api/devices/pairing").json()["code"]
    tunnel = make_client("local", base_url="http://localhost:8766")
    headers = {
        "Origin": "https://gaelb.example.ts.net",
        "X-Forwarded-Host": "gaelb.example.ts.net",
        "X-Forwarded-Proto": "https",
    }
    paired = tunnel.post("/api/devices/pair", json={"code": code}, headers=headers)
    assert paired.status_code == 200
    assert "Secure" in paired.headers["set-cookie"]


def test_server_info(make_client: MakeClient, settings: Settings) -> None:
    info = make_client("home").get("/api/server").json()
    assert info["url"] == f"http://192.168.1.20:{settings.home_port}"
    assert info["home_url"] == info["url"]
    assert info["home_reachable"] is True
    assert info["remote_url"] is None


def test_pairing_offers_no_home_link_phones_cannot_reach(make_client: MakeClient) -> None:
    from karaoke_server.network import NetworkState

    services = make_client("local").app.state.services  # type: ignore[attr-defined]
    # WSL in NAT mode: the Wi-Fi address belongs to Windows, which does not pass phones through.
    services.network.state = NetworkState("nat", "192.168.1.38", "laptop.tail.ts.net", 8766)
    pairing = make_client("local").post("/api/devices/pairing").json()
    assert pairing["urls"]["home"] is None
    assert (
        pairing["urls"]["remote"] == f"https://laptop.tail.ts.net/vincular?code={pairing['code']}"
    )
