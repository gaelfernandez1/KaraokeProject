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


class TestCeleryBrokerConfig:
    def test_broker_and_backend_fall_back_to_redis_url(self, monkeypatch):
        from karaoke.workers.celery_app import make_celery

        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://example:6379/2")
        celery = make_celery()
        assert celery.conf.broker_url == "redis://example:6379/2"
        assert celery.conf.result_backend == "redis://example:6379/2"

    def test_explicit_celery_vars_override_redis_url(self, monkeypatch):
        from karaoke.workers.celery_app import make_celery

        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://backend:6379/1")
        monkeypatch.setenv("REDIS_URL", "redis://example:6379/2")
        celery = make_celery()
        assert celery.conf.broker_url == "redis://broker:6379/0"
        assert celery.conf.result_backend == "redis://backend:6379/1"
