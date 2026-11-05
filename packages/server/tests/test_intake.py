import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import anyio
import pytest
from starlette.requests import ClientDisconnect

from karaoke_server.jobs.intake import IntakeError, media_info, receive_form

pytestmark = pytest.mark.anyio

BOUNDARY = "xyz123"


def multipart(fields: dict[str, str], file: tuple[str, bytes] | None = None) -> bytes:
    parts = []
    for name, value in fields.items():
        disposition = f'Content-Disposition: form-data; name="{name}"'
        parts.append(f"--{BOUNDARY}\r\n{disposition}\r\n\r\n{value}\r\n".encode())
    if file:
        name, data = file
        head = (
            f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        parts.append(head + data + b"\r\n")
    return b"".join(parts) + f"--{BOUNDARY}--\r\n".encode()


def headers(body: bytes, length: bool = True) -> dict[str, str]:
    result = {"content-type": f"multipart/form-data; boundary={BOUNDARY}"}
    if length:
        result["content-length"] = str(len(body))
    return result


async def chunks(
    body: bytes, size: int = 1000, cut_after: int | None = None
) -> AsyncIterator[bytes]:
    for start in range(0, len(body), size):
        if cut_after is not None and start >= cut_after:
            raise ClientDisconnect()
        yield body[start : start + size]


async def test_fields_and_file_go_to_disk(tmp_path: Path) -> None:
    body = multipart({"language": "gl", "lyrics": "Ola mar"}, ("Banda - Canción.mp3", b"x" * 5000))
    form = await receive_form(headers(body), chunks(body), tmp_path, max_bytes=10_000)
    assert form.fields == {"language": "gl", "lyrics": "Ola mar"}
    assert form.filename == "Banda - Canción.mp3"
    assert form.file is not None
    assert form.file.parent == tmp_path
    assert form.file.suffix == ".mp3"
    assert form.file.read_bytes() == b"x" * 5000


async def test_upload_over_the_limit_is_413_before_reading(tmp_path: Path) -> None:
    body = multipart({"language": "gl"}, ("a.mp3", b"x" * 400_000))

    async def never() -> AsyncIterator[bytes]:
        raise AssertionError("the body should not be read")
        yield b""

    with pytest.raises(IntakeError) as caught:
        await receive_form(headers(body), never(), tmp_path, max_bytes=100)
    assert (caught.value.status, caught.value.code) == (413, "too_big")


async def test_upload_without_length_is_refused(tmp_path: Path) -> None:
    body = multipart({"language": "gl"})
    with pytest.raises(IntakeError) as caught:
        await receive_form(headers(body, length=False), chunks(body), tmp_path, max_bytes=100)
    assert caught.value.status == 411


async def test_not_multipart_is_refused(tmp_path: Path) -> None:
    with pytest.raises(IntakeError) as caught:
        await receive_form(
            {"content-type": "application/json", "content-length": "2"},
            chunks(b"{}"),
            tmp_path,
            max_bytes=100,
        )
    assert caught.value.code == "bad_form"


async def test_upload_cut_midway_leaves_nothing(tmp_path: Path) -> None:
    body = multipart({"language": "gl"}, ("a.mp3", b"x" * 50_000))
    with pytest.raises(ClientDisconnect):
        await receive_form(headers(body), chunks(body, cut_after=20_000), tmp_path, max_bytes=10**6)
    assert list(tmp_path.iterdir()) == []


async def test_long_text_fields_are_refused(tmp_path: Path) -> None:
    body = multipart({"lyrics": "la " * 30_000})
    with pytest.raises(IntakeError) as caught:
        await receive_form(headers(body), chunks(body), tmp_path, max_bytes=10**6)
    assert caught.value.code == "bad_form"


@pytest.mark.usefixtures("ffmpeg")
async def test_media_info_reads_duration_and_tags(tmp_path: Path) -> None:
    song = tmp_path / "song.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=d=3",
            "-metadata",
            "title=Mar de Vigo",
            "-metadata",
            "artist=Banda",
            str(song),
        ],
        check=True,
    )
    info = await media_info(song)
    assert info.has_audio
    assert 2.9 < info.duration < 3.2
    assert (info.title, info.artist) == ("Mar de Vigo", "Banda")


@pytest.mark.usefixtures("ffmpeg")
async def test_media_info_of_a_picture_has_no_audio(tmp_path: Path) -> None:
    picture = tmp_path / "x.png"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=16x16",
            "-frames:v",
            "1",
            str(picture),
        ],
        check=True,
    )
    assert not (await media_info(picture)).has_audio


@pytest.mark.usefixtures("ffmpeg")
async def test_media_info_of_garbage(tmp_path: Path) -> None:
    junk = tmp_path / "junk.mp3"
    junk.write_text("hello")
    with anyio.fail_after(30):
        info = await media_info(junk)
    assert not info.has_audio
