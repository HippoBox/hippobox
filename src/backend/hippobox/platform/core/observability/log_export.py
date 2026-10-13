import logging

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.observability.logging import RequestContextFilter

_LOG_HANDLER: LoggingHandler | None = None


def setup_log_export() -> None:
    """Bridge application/Uvicorn logs to OTLP; SDK shutdown flushes at process exit."""
    global _LOG_HANDLER
    if not SETTINGS.LOGS_ENABLED or _LOG_HANDLER is not None:
        return

    provider = LoggerProvider(
        resource=Resource.create(
            {
                "service.name": SETTINGS.OTEL_SERVICE_NAME,
                "service.version": "0.1.0",
                "deployment.environment": SETTINGS.APP_ENV,
            }
        ),
    )
    provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=SETTINGS.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=SETTINGS.OTEL_EXPORTER_OTLP_INSECURE,
                timeout=SETTINGS.OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS,
            )
        )
    )
    handler = LoggingHandler(logger_provider=provider)
    handler.addFilter(RequestContextFilter())
    # App and server logs propagate to uvicorn; access logs do not by default.
    # Avoid the root logger so exporter failures cannot feed back into OTLP.
    logging.getLogger("uvicorn").addHandler(handler)
    access_logger = logging.getLogger("uvicorn.access")
    if not access_logger.propagate:
        access_logger.addHandler(handler)
    _LOG_HANDLER = handler
