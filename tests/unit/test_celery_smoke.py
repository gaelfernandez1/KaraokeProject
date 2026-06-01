"""Smoke tests for Celery task registration — no task execution, no GPU required."""


class TestCeleryTasksRegistered:
    def test_process_automatic_task_name(self):
        from karaoke.workers.celery_tasks import process_automatic_karaoke

        assert process_automatic_karaoke.name == "process_automatic_karaoke"

    def test_process_manual_lyrics_task_name(self):
        from karaoke.workers.celery_tasks import process_manual_lyrics_karaoke

        assert process_manual_lyrics_karaoke.name == "process_manual_lyrics_karaoke"

    def test_process_instrumental_task_name(self):
        from karaoke.workers.celery_tasks import process_instrumental_only

        assert process_instrumental_only.name == "process_instrumental_only"

    def test_all_tasks_are_callable(self):
        from karaoke.workers.celery_tasks import (
            process_automatic_karaoke,
            process_instrumental_only,
            process_manual_lyrics_karaoke,
        )

        assert callable(process_automatic_karaoke)
        assert callable(process_manual_lyrics_karaoke)
        assert callable(process_instrumental_only)
