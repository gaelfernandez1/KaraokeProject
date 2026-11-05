"""What the server exchanges with the web app (the shapes of decision 010).

The web's TypeScript types are generated from the OpenAPI description these models produce.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

LyricsSource = Literal["user", "asr", "lrclib"]


class SongSummary(BaseModel):
    """A song in the library, without its lyrics."""

    id: str
    title: str
    artist: str | None
    language: str
    duration: float
    cover: str | None
    has_video: bool
    created_at: str
    edited: bool
    lyrics_source: LyricsSource
    hook: str | None


class Device(BaseModel):
    """A device paired with the server: it may create, correct and delete songs."""

    id: str
    name: str
    created_at: str
    last_seen: str


# Party mode: one TV (the host) plays the songs; guests' phones request songs and act as remote
# controls. The server keeps this state and relays it; every client works out the turn order
# from it with the same function (`upcoming` in web/src/lib/party/rotation.ts).

QueueItemState = Literal["queued", "playing", "done", "skipped"]


class Guest(BaseModel):
    id: str
    name: str
    # One of the singer colours: it stands for this person on every screen.
    color: str
    # Milliseconds since the epoch.
    joined_at: int


class QueueItem(BaseModel):
    id: str
    guest_id: str
    song_id: str
    title: str
    artist: str | None
    duration: float
    added_at: int
    state: QueueItemState
    # Put first by the host.
    promoted: bool


class Playback(BaseModel):
    """What the TV is playing, published by the TV so phones can show it."""

    item_id: str | None
    playing: bool
    # Song position in seconds at `at` (milliseconds since the epoch).
    position: float
    at: int
    vocals: float
    pitch: float


class PartySettings(BaseModel):
    # Whether guests may pause, skip and change the sound, or only request songs.
    guests_control: bool


class PartyState(BaseModel):
    code: str
    # Goes up with every change; a client ignores a state older than the one it has.
    version: int
    guests: list[Guest]
    queue: list[QueueItem]
    playback: Playback
    settings: PartySettings


class SimpleCommand(BaseModel):
    type: Literal["play", "pause", "skip"]


class ValueCommand(BaseModel):
    type: Literal["vocals", "pitch"]
    value: float


PartyCommand = Annotated[SimpleCommand | ValueCommand, Field(discriminator="type")]


class PartyCreated(BaseModel):
    code: str
    host_token: str


class Joined(BaseModel):
    guest: Guest
    token: str


# Jobs: `make` turns a song into a karaoke; `export` renders its MP4.

JobStage = Literal[
    "queued",
    "download",
    "separate",
    "transcribe",
    "align",
    "audio",
    "video",
    "done",
    "error",
    "cancelled",
]

# Stable reasons a job failed, for the web to explain in the singer's language.
ErrorCode = Literal[
    "too_big",
    "too_long",
    "no_audio",
    "unreadable",
    "bad_url",
    "download_failed",
    "disk_full",
    "bad_lyrics",
    "gpu_memory",
    "out_of_memory",
    "engine_failed",
    "interrupted",
    "song_missing",
]


class Job(BaseModel):
    id: str
    kind: Literal["make", "export"]
    # The song's title, as given or guessed from the file name, its tags or the link.
    title: str
    stage: JobStage
    # How far the current stage has gone, 0-1.
    progress: float
    # Set when a `make` job is done.
    song_id: str | None
    # Set when an `export` job is done: the MP4's path inside the song's package.
    file: str | None
    error: str | None
    error_code: ErrorCode | None
    # Whether the song came with lyrics (the transcription stage is skipped).
    with_lyrics: bool
    created_at: str
    # How far the whole job has gone, 0-1, from what each stage takes on this machine.
    overall: float | None
    # Estimated seconds left, while running.
    eta: float | None
    can_retry: bool
    attempt: int


class MakeRequest(BaseModel):
    language: str
    lyrics: str | None = None
    lrclib: bool = False
    title: str | None = None
    artist: str | None = None
    url: str | None = None


class ExportRequest(BaseModel):
    aspect: Literal["16:9", "9:16"] = "16:9"
    theme: str = "clasico"
