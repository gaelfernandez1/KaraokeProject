"""Party rooms: guests, the queue, what the TV plays and what guests may do.

The same rules as the web's development stand-in (`web/dev/mock/party.ts`), kept in memory for
speed and saved to the database after every change, so a restart does not end the party.
Tokens are stored as hashes; a guest who joins again by name gets a fresh token for the same
identity.
"""

import hashlib
import json
import logging
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from karaoke_server.db import Database
from karaoke_server.library import Library
from karaoke_server.models import (
    Guest,
    Joined,
    PartyCreated,
    PartySettings,
    PartyState,
    Playback,
    QueueItem,
    QueueItemState,
    SimpleCommand,
    ValueCommand,
)

logger = logging.getLogger(__name__)

# No vowels, so a code never spells a word.
CODE_LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
MAX_NAME = 24
MAX_GUESTS = 50
# A party nobody touched for this long is over.
EXPIRE_HOURS = 24
# The first is orange, not the lyric amber, which means "sung".
SINGER_COLORS = ("#FF8A3D", "#4FD1FF", "#FF6FB5", "#7CE38B")

Event = Literal["state", "command"]
Listener = Callable[[Event, PartyState | SimpleCommand | ValueCommand], None]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class _Room:
    state: PartyState
    host_hash: str
    # Token hash → guest id.
    tokens: dict[str, str]
    next_id: int = 1
    updated: float = 0.0
    listeners: list[tuple[str | None, Listener]] = field(default_factory=list)

    def new_id(self, prefix: str) -> str:
        self.next_id += 1
        return f"{prefix}{self.next_id - 1}"


class Parties:
    def __init__(
        self, db: Database, library: Library, now: Callable[[], float] = time.time
    ) -> None:
        self.db = db
        self.library = library
        self.now = now
        self._rooms: dict[str, _Room] = {}

    def _ms(self) -> int:
        return int(self.now() * 1000)

    # Rooms

    def create(self) -> PartyCreated:
        self.expire()
        code = ""
        while not code or code in self._rooms:
            code = "".join(secrets.choice(CODE_LETTERS) for _ in range(4))
        host_token = secrets.token_urlsafe(16)
        playback = Playback(
            item_id=None, playing=False, position=0, at=self._ms(), vocals=0.15, pitch=0
        )
        state = PartyState(
            code=code,
            version=1,
            guests=[],
            queue=[],
            playback=playback,
            settings=PartySettings(guests_control=False),
        )
        room = _Room(state=state, host_hash=_hash(host_token), tokens={})
        self._rooms[code] = room
        self._save(room)
        return PartyCreated(code=code, host_token=host_token)

    def get(self, code: str) -> PartyState | None:
        room = self._rooms.get(code.upper())
        return room.state if room else None

    def is_host(self, code: str, who: str) -> bool:
        room = self._rooms.get(code.upper())
        return room is not None and _hash(who) == room.host_hash

    def load(self) -> None:
        """Brings back the parties saved before a restart."""
        for row in self.db.query("SELECT code, data FROM parties"):
            try:
                saved = json.loads(row["data"])
                room = _Room(
                    state=PartyState.model_validate(saved["state"]),
                    host_hash=saved["host_hash"],
                    tokens=saved["tokens"],
                    next_id=saved["next_id"],
                    updated=saved["updated"],
                )
            except (ValueError, KeyError):
                logger.warning("dropping a party that could not be read: %s", row["code"])
                self.db.execute("DELETE FROM parties WHERE code = ?", (row["code"],))
                continue
            self._rooms[room.state.code] = room
        self.expire()

    def expire(self, hours: float = EXPIRE_HOURS) -> None:
        limit = self.now() - hours * 3600
        for code, room in list(self._rooms.items()):
            if room.updated < limit:
                del self._rooms[code]
        self.db.execute("DELETE FROM parties WHERE updated_at < ?", (limit,))

    # Guests and the queue

    def join(self, code: str, name: str) -> Joined | None:
        """Joining again with the same name (any case or spacing) is the same guest."""
        room = self._rooms.get(code.upper())
        clean = re.sub(r"\s+", " ", name.strip())[:MAX_NAME].strip()
        if room is None or not clean:
            return None
        key = clean.casefold()
        guest = next((g for g in room.state.guests if g.name.casefold() == key), None)
        token = secrets.token_urlsafe(16)
        if guest is None:
            if len(room.state.guests) >= MAX_GUESTS:
                return None
            color = SINGER_COLORS[len(room.state.guests) % len(SINGER_COLORS)]
            guest = Guest(id=room.new_id("g"), name=clean, color=color, joined_at=self._ms())
            room.state.guests.append(guest)
            room.tokens[_hash(token)] = guest.id
            self._changed(room)
        else:
            # Nothing anyone sees changes: only the new token is kept.
            room.tokens[_hash(token)] = guest.id
            self._save(room)
        return Joined(guest=guest, token=token)

    def enqueue(self, code: str, who: str, song_id: str) -> QueueItem | None:
        room = self._rooms.get(code.upper())
        guest_id = room.tokens.get(_hash(who)) if room else None
        song = self.library.summary(song_id)
        if room is None or guest_id is None or song is None:
            return None
        item = QueueItem(
            id=room.new_id("q"),
            guest_id=guest_id,
            song_id=song_id,
            title=song.title,
            artist=song.artist,
            duration=song.duration,
            added_at=self._ms(),
            state="queued",
            promoted=False,
        )
        room.state.queue.append(item)
        self._changed(room)
        return item

    def remove(self, code: str, who: str, item_id: str) -> bool:
        """A guest removes their own queued songs; the host removes any."""
        room = self._rooms.get(code.upper())
        if room is None:
            return False
        queue = room.state.queue
        index = next(
            (i for i, it in enumerate(queue) if it.id == item_id and it.state == "queued"), None
        )
        if index is None:
            return False
        is_host = _hash(who) == room.host_hash
        if not is_host and room.tokens.get(_hash(who)) != queue[index].guest_id:
            return False
        del queue[index]
        self._changed(room)
        return True

    def command(self, code: str, who: str, command: SimpleCommand | ValueCommand) -> bool:
        """Relays a remote-control press to the TV: always from the host; from a guest if the
        host lets guests control, or if it is that guest's song that is playing."""
        room = self._rooms.get(code.upper())
        if room is None:
            return False
        guest = room.tokens.get(_hash(who))
        singing = any(i.state == "playing" and i.guest_id == guest for i in room.state.queue)
        allowed = _hash(who) == room.host_hash or (
            guest is not None and (room.state.settings.guests_control or singing)
        )
        if not allowed:
            return False
        for token_hash, listener in list(room.listeners):
            if token_hash == room.host_hash:
                listener("command", command)
        return True

    # Host only

    def publish_playback(self, code: str, who: str, playback: Playback) -> bool:
        def change(room: _Room) -> bool:
            room.state.playback = playback
            return True

        return self._as_host(code, who, change)

    def advance(self, code: str, who: str, item_id: str, state: QueueItemState) -> bool:
        """The host marks a song as playing, done or skipped; only one song plays at a time."""

        def change(room: _Room) -> bool:
            item = next((i for i in room.state.queue if i.id == item_id), None)
            if item is None:
                return False
            if state == "playing":
                for other in room.state.queue:
                    if other.state == "playing":
                        other.state = "done"
            item.state = state
            return True

        return self._as_host(code, who, change)

    def promote(self, code: str, who: str, item_id: str) -> bool:
        def change(room: _Room) -> bool:
            item = next((i for i in room.state.queue if i.id == item_id), None)
            if item is None:
                return False
            item.promoted = True
            return True

        return self._as_host(code, who, change)

    def update_settings(self, code: str, who: str, settings: PartySettings) -> bool:
        def change(room: _Room) -> bool:
            room.state.settings = settings.model_copy()
            return True

        return self._as_host(code, who, change)

    # Live updates

    def subscribe(
        self, code: str, who: str | None, listener: Listener
    ) -> Callable[[], None] | None:
        """Sends the current state at once, then every change (and commands, to the host)."""
        room = self._rooms.get(code.upper())
        if room is None:
            return None
        entry = (_hash(who) if who else None, listener)
        room.listeners.append(entry)
        listener("state", room.state)

        def unsubscribe() -> None:
            if entry in room.listeners:
                room.listeners.remove(entry)

        return unsubscribe

    def listener_count(self, code: str) -> int:
        room = self._rooms.get(code.upper())
        return len(room.listeners) if room else 0

    # Inside

    def _as_host(self, code: str, who: str, change: Callable[[_Room], bool]) -> bool:
        room = self._rooms.get(code.upper())
        if room is None or _hash(who) != room.host_hash:
            return False
        if not change(room):
            return False
        self._changed(room)
        return True

    def _changed(self, room: _Room) -> None:
        room.state.version += 1
        self._save(room)
        for _, listener in list(room.listeners):
            listener("state", room.state)

    def _save(self, room: _Room) -> None:
        room.updated = self.now()
        data = {
            "state": room.state.model_dump(mode="json"),
            "host_hash": room.host_hash,
            "tokens": room.tokens,
            "next_id": room.next_id,
            "updated": room.updated,
        }
        self.db.execute(
            "INSERT OR REPLACE INTO parties (code, data, updated_at) VALUES (?, ?, ?)",
            (room.state.code, json.dumps(data), room.updated),
        )
