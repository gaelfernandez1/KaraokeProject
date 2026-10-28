import logging

from karaoke.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    """Wire up Sentry if a DSN is configured; a no-op otherwise.

    The sentry-sdk[flask,celery] extras auto-enable the Flask and Celery
    integrations in whichever process imports them, so the same call covers both
    the web app (create_app) and the Celery worker bootstrap.
    """
    if not settings.sentry_dsn:
        return

    import sentry_sdk  # noqa: PLC0415

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        # Never ship request bodies, headers or user emails to Sentry: magic-link
        # logins put the email in the request, and PII must stay out of the dashboard.
        send_default_pii=False,
    )
    logger.info("Sentry initialized")
