"""Worker/Beat entry point: celery -A app.core.celery.app:celery_app."""

import logging

from celery import Celery, Task
from celery.signals import after_setup_logger

from hippobox.platform.core.config.settings import SETTINGS, Settings
from hippobox.platform.core.observability.logging import RequestContextFilter, configure_request_context_logging
from hippobox.platform.core.observability.task_context import task_log_context


class ContextTask(Task):
    """Bind correlation IDs only for the lifetime of this task execution."""

    abstract = True

    def __call__(self, *args: object, **kwargs: object) -> object:
        headers = self.request.headers or {}
        with task_log_context(
            task_id=self.request.id or "", trace_id=str(headers.get("trace_id") or "")
        ):
            return super().__call__(*args, **kwargs)


def create_celery_app(settings: Settings) -> Celery:
    app = Celery(
        "b4fastapi",
        broker=settings.celery_broker_url,
        task_cls=ContextTask,
        include=[
            "hippobox.platform.core.celery.tasks",
            "hippobox.platform.core.celery.mail",
            "hippobox.platform.core.celery.notifications",
            "hippobox.platform.core.celery.billing",
        ],
    )
    app.conf.update(
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        task_ignore_result=True,
        result_backend=None,
        enable_utc=True,
        timezone="UTC",
        task_default_queue=settings.CELERY_QUEUE,
        broker_transport_options={
            "global_keyprefix": settings.CELERY_KEY_PREFIX,
            "visibility_timeout": 3600,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        },
        visibility_timeout=3600,
        broker_connection_timeout=5,
        broker_connection_retry_on_startup=True,
        task_publish_retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 0.2},
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        # Worker loss redelivers unacked tasks; domain handlers must be idempotent.
        task_reject_on_worker_lost=True,
        task_soft_time_limit=240,
        task_time_limit=300,
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=False,
        beat_schedule={
            "lifecycle-mail-outbox": {"task": "b4fastapi.notifications.drain", "schedule": 60.0},
            "billing-reconciliation": {"task": "b4fastapi.billing.reconcile", "schedule": 300.0},
        },
    )
    return app


@after_setup_logger.connect
def configure_worker_logging(logger: logging.Logger, **kwargs: object) -> None:
    configure_request_context_logging()
    for handler in logger.handlers:
        handler.addFilter(RequestContextFilter())
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s%(request_context)s %(message)s")
        )


celery_app = create_celery_app(SETTINGS)
