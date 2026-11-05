"""Song titles from file names and video pages, cleaned so LRCLIB can find their lyrics."""

import re

_NOISE = re.compile(
    r"\s*[\(\[][^\)\]]*\b(official|oficial|video|vídeo|videoclip|lyrics?|letra|audio|"
    r"visuali[sz]er|hd|4k|remaster(ed)?|live|en directo|ao vivo)\b[^\)\]]*[\)\]]",
    re.IGNORECASE,
)
_FEATURING = re.compile(r"\s+[\(\[]?(ft\.?|feat\.?|featuring)\s+[^\)\]]*[\)\]]?$", re.IGNORECASE)
_ARTIST_NOISE = re.compile(r"\s*(-\s*topic|vevo|official)$", re.IGNORECASE)
# A track number in front, as album files are named: «06. Title», «01 - Title», «2_title».
_TRACK = re.compile(r"^\d{1,3}(?:\s*\.\s*|\s+-\s+|_+)(?=[^\d\s])")


def clean_title(title: str) -> str:
    text = _TRACK.sub("", title.strip())
    cleaned = _FEATURING.sub("", _NOISE.sub("", text)).strip(" -|")
    if " " not in cleaned:
        # A file name: its spaces were written as underscores.
        cleaned = cleaned.replace("_", " ").strip()
    return cleaned or title.strip()


def clean_artist(artist: str | None) -> str | None:
    if not artist:
        return None
    first = artist.split(",")[0]
    cleaned = _ARTIST_NOISE.sub("", first).strip()
    return cleaned or None


def split_artist(title: str) -> tuple[str | None, str]:
    """«Artist - Title» (how many videos and files are named) → (artist, title)."""
    if " - " in title:
        artist, rest = title.split(" - ", 1)
        if artist.strip() and rest.strip():
            return artist.strip(), rest.strip()
    return None, title
