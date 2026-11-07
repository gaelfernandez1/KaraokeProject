from karaoke_server.db import Database
from karaoke_server.jobs.store import JobRecord, JobStore


def test_round_trip_and_update(db: Database) -> None:
    store = JobStore(db)
    record = JobRecord.new("j1", "make", "Mar", {"language": "gl", "url": "https://x"}, now=1.0)
    store.add(record)
    store.update("j1", stage="download", progress=0.5, stage_seconds={"download": 3.0})
    loaded = store.get("j1")
    assert loaded is not None
    assert (loaded.stage, loaded.progress) == ("download", 0.5)
    assert loaded.request["url"] == "https://x"
    assert loaded.stage_seconds == {"download": 3.0}
    assert store.get("nope") is None


def test_lanes_pick_the_oldest_ready_job(db: Database) -> None:
    store = JobStore(db)
    store.add(JobRecord.new("link", "make", "A", {"language": "gl", "url": "https://x"}, now=1.0))
    upload = JobRecord.new("upload", "make", "B", {"language": "gl"}, now=2.0)
    upload.source = "/data/jobs/upload/source.mp3"
    store.add(upload)
    store.add(JobRecord.new("export", "export", "C", {"song_id": "s"}, now=3.0))
    assert store.next_for_download().id == "link"  # type: ignore[union-attr]
    assert store.next_for_gpu().id == "upload"  # type: ignore[union-attr]
    store.update("upload", stage="done")
    assert store.next_for_gpu().id == "export"  # type: ignore[union-attr]


def test_list_newest_first_and_history(db: Database) -> None:
    store = JobStore(db)
    for n in range(3):
        record = JobRecord.new(f"j{n}", "make", "x", {"language": "gl"}, now=float(n))
        record.stage = "done"
        record.duration = 100.0
        record.stage_seconds = {"separate": 20.0 + n}
        store.add(record)
    assert [r.id for r in store.recent()] == ["j2", "j1", "j0"]
    assert sorted(store.stage_history("separate")) == [0.2, 0.21, 0.22]
    assert store.stage_history("align") == []


def test_an_export_saved_without_its_song_still_names_it(db: Database) -> None:
    # Exports used to keep their song only in the request: those jobs must still show in the
    # song's download panel.
    store = JobStore(db)
    store.add(JobRecord.new("old", "export", "Mar", {"song_id": "mar", "aspect": "16:9"}, now=1.0))
    db.execute("UPDATE jobs SET song_id = NULL WHERE id = 'old'")
    loaded = store.get("old")
    assert loaded is not None
    assert loaded.song_id == "mar"
