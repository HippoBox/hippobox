from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from hippobox.platform.core.config.settings import SETTINGS

METRICS_PATH = "/metrics"


def setup_metrics(app: FastAPI) -> None:
    if not SETTINGS.METRICS_ENABLED:
        return

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=False,
        excluded_handlers=[METRICS_PATH],
        registry=CollectorRegistry(auto_describe=True),
    )
    instrumentator.instrument(app).expose(
        app,
        endpoint=METRICS_PATH,
        include_in_schema=False,
        should_gzip=True,
    )
