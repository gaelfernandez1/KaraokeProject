import json
import time
from collections.abc import Callable

import httpx

from karaoke_server.config import Settings

from .conftest import MakeClient, write_package
from .live import live_server, read_events


def test_party_routes_follow_the_mock(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "demo-sintetico")
    tv = make_client("local")
    phone = make_client("home")
    created = tv.post("/api/parties")
    assert created.status_code == 201
    code, host = created.json()["code"], created.json()["host_token"]
    assert phone.get(f"/api/parties/{code.lower()}").json()["version"] == 1
    assert phone.get("/api/parties/ZZZZ").status_code == 404
    assert phone.post(f"/api/parties/{code}/guests", json={"name": " "}).status_code == 422
    joined = phone.post(f"/api/parties/{code}/guests", json={"name": "Ana"})
    assert joined.status_code == 201
    token = joined.json()["token"]
    auth = {"Authorization": f"Bearer {token}"}
    item = phone.post(
        f"/api/parties/{code}/queue", json={"song_id": "demo-sintetico"}, headers=auth
    )
    assert item.status_code == 201
    item_id = item.json()["id"]
    host_auth = {"Authorization": f"Bearer {host}"}
    assert (
        phone.put(
            f"/api/parties/{code}/advance",
            json={"item_id": item_id, "state": "playing"},
            headers=auth,
        ).status_code
        == 403
    )
    assert (
        tv.put(
            f"/api/parties/{code}/advance",
            json={"item_id": item_id, "state": "playing"},
            headers=host_auth,
        ).status_code
        == 204
    )
    assert (
        phone.post(
            f"/api/parties/{code}/commands", json={"type": "pause"}, headers=auth
        ).status_code
        == 204
    )
    assert (
        phone.post(
            f"/api/parties/{code}/commands", json={"type": "dance"}, headers=auth
        ).status_code
        == 422
    )
    assert (
        tv.put(
            f"/api/parties/{code}/settings", json={"guests_control": True}, headers=host_auth
        ).status_code
        == 204
    )
    playback = {
        "item_id": item_id,
        "playing": True,
        "position": 3.0,
        "at": 1,
        "vocals": 0.2,
        "pitch": 0,
    }
    assert (
        tv.put(f"/api/parties/{code}/playback", json=playback, headers=host_auth).status_code == 204
    )
    assert tv.post(f"/api/parties/{code}/promote/{item_id}", headers=host_auth).status_code == 204
    assert phone.delete(f"/api/parties/{code}/queue/{item_id}", headers=auth).status_code == 403


def test_create_party_from_remote_needs_owner(make_client: MakeClient) -> None:
    assert make_client("remote").post("/api/parties").status_code == 403
    assert make_client("home").post("/api/parties").status_code == 201


def _app(make_client: MakeClient):  # type: ignore[no-untyped-def]
    return make_client("local").app


def test_sse_sends_state_on_connect_and_on_change(
    settings: Settings, make_client: MakeClient
) -> None:
    app = _app(make_client)
    with live_server(app) as base, httpx.Client(base_url=base, timeout=10) as http:
        code = http.post("/api/parties").json()["code"]
        with http.stream("GET", f"/api/parties/{code}/events") as stream:
            lines = stream.iter_lines()
            assert json.loads(read_events(lines, 1)[0][1])["version"] == 1
            http.post(f"/api/parties/{code}/guests", json={"name": "Ana"})
            event, data = read_events(lines, 1)[0]
            assert event == "state"
            assert json.loads(data)["guests"][0]["name"] == "Ana"


def test_sse_commands_reach_only_the_host(settings: Settings, make_client: MakeClient) -> None:
    app = _app(make_client)
    with live_server(app) as base, httpx.Client(base_url=base, timeout=10) as http:
        created = http.post("/api/parties").json()
        code, host = created["code"], created["host_token"]
        joined = http.post(f"/api/parties/{code}/guests", json={"name": "Ana"}).json()
        http.put(
            f"/api/parties/{code}/settings",
            json={"guests_control": True},
            headers={"Authorization": f"Bearer {host}"},
        )
        with http.stream("GET", f"/api/parties/{code}/events?token={host}") as stream:
            lines = stream.iter_lines()
            read_events(lines, 1)
            http.post(
                f"/api/parties/{code}/commands",
                json={"type": "skip"},
                headers={"Authorization": f"Bearer {joined['token']}"},
            )
            event, data = read_events(lines, 1)[0]
            assert (event, json.loads(data)) == ("command", {"type": "skip"})


def _wait_for(condition: Callable[[], bool], seconds: float = 5) -> bool:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.05)
    return condition()


def test_sse_unsubscribes_when_the_client_goes(make_client: MakeClient) -> None:
    app = _app(make_client)
    parties = app.state.services.parties
    with live_server(app) as base, httpx.Client(base_url=base, timeout=10) as http:
        code = http.post("/api/parties").json()["code"]
        with http.stream("GET", f"/api/parties/{code}/events") as stream:
            assert stream.status_code == 200
            seen = read_events(stream.iter_lines(), 1)
            assert seen, "the stream ended without an event"
            assert seen[0][0] == "state", seen
            assert json.loads(seen[0][1])["code"] == code, seen
            # The server registers the stream before it sends the first state; this failed once
            # in CI under the full parallel suite, so it now says what it saw if it fails again.
            assert _wait_for(lambda: parties.listener_count(code) == 1), (
                f"connected and got {seen}, but {parties.listener_count(code)} listeners"
            )
        assert _wait_for(lambda: parties.listener_count(code) == 0)


def test_sse_for_a_missing_party_is_404(make_client: MakeClient) -> None:
    assert make_client("local").get("/api/parties/ZZZZ/events").status_code == 404


def test_ending_the_party_closes_the_phones_streams(make_client: MakeClient) -> None:
    app = _app(make_client)
    with live_server(app) as base, httpx.Client(base_url=base, timeout=10) as http:
        created = http.post("/api/parties").json()
        code, host = created["code"], created["host_token"]
        with http.stream("GET", f"/api/parties/{code}/events") as stream:
            lines = stream.iter_lines()
            read_events(lines, 1)
            assert http.delete(f"/api/parties/{code}").status_code == 403  # not the TV
            ended = http.delete(f"/api/parties/{code}", headers={"Authorization": f"Bearer {host}"})
            assert ended.status_code == 204
            assert read_events(lines, 1)[0][0] == "ended"
            assert list(lines) == [] or all(not line.startswith("data") for line in lines)
        assert http.get(f"/api/parties/{code}").status_code == 404
