"""How long each stage takes, so the web can show real progress and the time left.

The engine only says when a stage starts, so a stage's progress is the time it has run against
what it usually takes here: the median of the last finished jobs on this machine (per second of
song), or a first guess measured on the RTX 3050 until there are a few.
"""

import statistics
from collections.abc import Callable

from karaoke_server.jobs.store import JobRecord

# The engine's steps (karaoke_engine.make) and the stages the web shows.
ENGINE_STAGE = {
    "decode": "separate",
    "separate": "separate",
    "transcribe": "transcribe",
    "align": "align",
    "encode": "audio",
}

# Stage → (fixed seconds, seconds per second of song), measured with the server on the
# RTX 3050 (bench/results/2026-11-05-c8-servidor). Downloads go by yt-dlp's own percentage.
DEFAULTS: dict[str, tuple[float, float]] = {
    "download": (5.0, 0.06),
    "separate": (4.0, 0.22),
    "transcribe": (8.0, 0.05),
    "align": (2.0, 0.033),
    "audio": (3.0, 0.1),
    "video": (5.0, 0.085),
}
TIME_BASED = ("separate", "transcribe", "align", "audio", "video")
# A stage that runs long sits here until it ends, instead of claiming to be finished.
CEILING = 0.97
# For estimates before the song's length is known (a link not yet looked at).
TYPICAL_SONG = 240.0


def plan_for(record: JobRecord) -> list[str]:
    if record.kind == "export":
        return ["video"]
    stages = ["download"] if record.request.get("url") else []
    stages.append("separate")
    if not record.with_lyrics:
        stages.append("transcribe")
    return [*stages, "align", "audio"]


class Estimator:
    def __init__(self, history: Callable[[str], list[float]]) -> None:
        self.history = history

    def expected(self, stage: str, duration: float | None) -> float:
        seconds = duration or TYPICAL_SONG
        past = self.history(stage)
        if len(past) >= 3:
            return statistics.median(past) * seconds
        fixed, rate = DEFAULTS.get(stage, (5.0, 0.1))
        return fixed + rate * seconds

    def stage_progress(self, stage: str, elapsed: float, duration: float | None) -> float:
        expected = self.expected(stage, duration)
        return min(CEILING, max(0.0, elapsed / expected)) if expected > 0 else 0.0

    def _current(self, record: JobRecord, now: float) -> float:
        """Seconds of the current stage that count as done."""
        if record.stage == "download":
            return self.expected("download", record.duration) * record.progress
        elapsed = now - (record.stage_started or now)
        return self.stage_progress(record.stage, elapsed, record.duration) * self.expected(
            record.stage, record.duration
        )

    def overall(self, record: JobRecord, now: float) -> float | None:
        if record.stage == "done":
            return 1.0
        if record.stage in ("error", "cancelled"):
            return None
        plan = plan_for(record)
        sizes = [self.expected(stage, record.duration) for stage in plan]
        total = sum(sizes)
        if record.stage == "queued":
            # Waiting for the GPU after downloading: the download is done.
            done = sizes[0] if plan[0] == "download" and record.source else 0.0
            return done / total
        if record.stage not in plan:
            return None
        index = plan.index(record.stage)
        return (sum(sizes[:index]) + self._current(record, now)) / total

    def eta(self, record: JobRecord, now: float) -> float | None:
        if record.stage not in plan_for(record):
            return None
        plan = plan_for(record)
        index = plan.index(record.stage)
        current = self.expected(record.stage, record.duration) - self._current(record, now)
        later = sum(self.expected(stage, record.duration) for stage in plan[index + 1 :])
        return max(0.0, current) + later
