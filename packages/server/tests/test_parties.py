import pytest

from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.library import Library
from karaoke_server.models import PartySettings, Playback, SimpleCommand, ValueCommand
from karaoke_server.parties import MAX_GUESTS, Parties

from .conftest import write_package


class Clock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def library(settings: Settings, db: Database) -> Library:
    write_package(settings.library_dir / "demo-sintetico", title="Title demo-sintetico")
    return Library(settings, db)


@pytest.fixture
def parties(db: Database, library: Library, clock: Clock) -> Parties:
    return Parties(db, library, now=clock)


def pause() -> SimpleCommand:
    return SimpleCommand(type="pause")


def test_makes_four_letter_codes(parties: Parties) -> None:
    code = parties.create().code
    assert len(code) == 4
    assert set(code) <= set("BCDFGHJKLMNPQRSTVWXZ")
    assert parties.get(code.lower()) is not None


def test_a_guest_who_joins_again_with_the_same_name_is_the_same(parties: Parties) -> None:
    code = parties.create().code
    first = parties.join(code, "Ana")
    again = parties.join(code, " ana ")
    assert first
    assert again
    assert again.guest.id == first.guest.id
    assert again.guest.color == first.guest.color
    assert parties.get(code).guests[0].name == "Ana"  # type: ignore[union-attr]


def test_names_are_trimmed_and_needed(parties: Parties) -> None:
    code = parties.create().code
    assert parties.join(code, "   ") is None
    joined = parties.join(code, "  Brais   da   Ponte " + "x" * 40)
    assert joined is not None
    assert joined.guest.name.startswith("Brais da Ponte")
    assert len(joined.guest.name) == 24


def test_hands_out_the_singer_colours_in_order(parties: Parties) -> None:
    code = parties.create().code
    colors = [parties.join(code, n).guest.color for n in "ABCDE"]  # type: ignore[union-attr]
    assert colors == ["#FF8A3D", "#4FD1FF", "#FF6FB5", "#7CE38B", "#FF8A3D"]


def test_bumps_the_version_and_tells_the_subscribers(parties: Parties) -> None:
    code = parties.create().code
    versions: list[int] = []
    parties.subscribe(code, None, lambda event, data: versions.append(data.version))  # type: ignore[union-attr]
    joined = parties.join(code, "Ana")
    assert joined
    item = parties.enqueue(code, joined.token, "demo-sintetico")
    assert item is not None
    assert item.title == "Title demo-sintetico"
    assert parties.remove(code, joined.token, item.id)
    assert len(versions) == 4
    assert versions == sorted(versions)
    assert parties.get(code).queue == []  # type: ignore[union-attr]


def test_only_guests_queue_existing_songs(parties: Parties) -> None:
    created = parties.create()
    joined = parties.join(created.code, "Ana")
    assert joined
    assert parties.enqueue(created.code, created.host_token, "demo-sintetico") is None
    assert parties.enqueue(created.code, joined.token, "missing") is None
    assert parties.enqueue(created.code, "nobody", "demo-sintetico") is None


def test_only_lets_a_guest_remove_their_own_songs(parties: Parties) -> None:
    created = parties.create()
    ana = parties.join(created.code, "Ana")
    brais = parties.join(created.code, "Brais")
    assert ana
    assert brais
    item = parties.enqueue(created.code, ana.token, "demo-sintetico")
    assert item
    assert parties.remove(created.code, brais.token, item.id) is False
    assert parties.remove(created.code, created.host_token, item.id) is True


def test_the_singer_controls_their_own_song(parties: Parties) -> None:
    created = parties.create()
    ana = parties.join(created.code, "Ana")
    brais = parties.join(created.code, "Brais")
    assert ana
    assert brais
    item = parties.enqueue(created.code, ana.token, "demo-sintetico")
    assert item
    assert parties.advance(created.code, created.host_token, item.id, "playing")
    assert parties.command(created.code, ana.token, pause()) is True
    assert parties.command(created.code, brais.token, pause()) is False


def test_guest_commands_reach_the_host_only_when_allowed(parties: Parties) -> None:
    created = parties.create()
    commands: list[object] = []
    guests_saw: list[str] = []

    def on_host(event: str, data: object) -> None:
        if event == "command":
            commands.append(data)

    parties.subscribe(created.code, created.host_token, on_host)
    joined = parties.join(created.code, "Ana")
    assert joined
    parties.subscribe(created.code, joined.token, lambda event, data: guests_saw.append(event))
    assert parties.command(created.code, joined.token, pause()) is False
    assert parties.update_settings(
        created.code, created.host_token, PartySettings(guests_control=True)
    )
    assert parties.command(created.code, joined.token, ValueCommand(type="vocals", value=0.5))
    assert [c.model_dump() for c in commands] == [{"type": "vocals", "value": 0.5}]  # type: ignore[attr-defined]
    assert "command" not in guests_saw


def test_only_one_song_plays_at_a_time(parties: Parties) -> None:
    created = parties.create()
    ana = parties.join(created.code, "Ana")
    assert ana
    first = parties.enqueue(created.code, ana.token, "demo-sintetico")
    second = parties.enqueue(created.code, ana.token, "demo-sintetico")
    assert first
    assert second
    parties.advance(created.code, created.host_token, first.id, "playing")
    parties.advance(created.code, created.host_token, second.id, "playing")
    states = {i.id: i.state for i in parties.get(created.code).queue}  # type: ignore[union-attr]
    assert states == {first.id: "done", second.id: "playing"}
    assert parties.advance(created.code, ana.token, second.id, "done") is False
    assert parties.promote(created.code, created.host_token, second.id) is True
    assert parties.promote(created.code, created.host_token, "nope") is False


def test_playback_is_published_by_the_host(parties: Parties, clock: Clock) -> None:
    created = parties.create()
    playback = Playback(
        item_id=None, playing=True, position=12.5, at=int(clock.t * 1000), vocals=0.3, pitch=-2
    )
    assert parties.publish_playback(created.code, created.host_token, playback)
    assert parties.get(created.code).playback.position == 12.5  # type: ignore[union-attr]


def test_state_survives_a_restart(db: Database, library: Library, clock: Clock) -> None:
    first = Parties(db, library, now=clock)
    created = first.create()
    ana = first.join(created.code, "Ana")
    assert ana
    first.enqueue(created.code, ana.token, "demo-sintetico")
    again = Parties(db, library, now=clock)
    again.load()
    state = again.get(created.code)
    assert state is not None
    assert [g.name for g in state.guests] == ["Ana"]
    assert len(state.queue) == 1
    assert again.is_host(created.code, created.host_token)
    assert again.enqueue(created.code, ana.token, "demo-sintetico") is not None
    rejoined = again.join(created.code, "ana")
    assert rejoined
    assert rejoined.guest.id == ana.guest.id
    ids = [i.id for i in again.get(created.code).queue]  # type: ignore[union-attr]
    assert len(set(ids)) == len(ids)


def test_expired_parties_are_gone(db: Database, library: Library, clock: Clock) -> None:
    parties = Parties(db, library, now=clock)
    code = parties.create().code
    clock.t += 25 * 3600
    parties.expire()
    assert parties.get(code) is None
    later = Parties(db, library, now=clock)
    later.load()
    assert later.get(code) is None


def test_guest_limit(parties: Parties) -> None:
    code = parties.create().code
    for n in range(MAX_GUESTS):
        assert parties.join(code, f"Guest {n}") is not None
    assert parties.join(code, "One too many") is None
    assert parties.join(code, "guest 3") is not None
