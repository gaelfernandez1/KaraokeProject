import math


def sec2tc(sec_float: float) -> str:
    ms = int(math.floor(sec_float * 1000))
    hh = ms // 3600000
    mm = (ms % 3600000) // 60000
    ss = (ms % 60000) // 1000
    ms = ms % 1000
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


def build_word_srt(word_segments: list[dict], speaker_colors: dict | None = None) -> str:
    """Build a word-level SRT string from whisperx word_segments.

    whisperx leaves words it cannot force-align without start/end timestamps
    (missing keys, or None), which happens often with manual lyrics in a
    language the alignment model handles poorly. Skip those words instead of
    crashing the whole request on a KeyError.
    """
    blocks: list[str] = []
    index = 1
    for seg in word_segments:
        if "word" not in seg:
            continue
        start = seg.get("start")
        end = seg.get("end")
        if start is None or end is None:
            continue
        text = seg["word"].strip()
        if speaker_colors and "speaker" in seg:
            color = speaker_colors.get(seg["speaker"], "#FFFFFF")
            text = f"{seg['speaker']}|{color}|{text}"
        blocks.append(f"{index}\n{sec2tc(start)} --> {sec2tc(end)}\n{text}\n\n")
        index += 1
    return "".join(blocks)
