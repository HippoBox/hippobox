from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from sqlalchemy.ext.asyncio import AsyncEngine

from hippobox.platform.core.config.settings import SETTINGS

TRACING_EXCLUDED_URLS = "/metrics,/health/live,/health/ready"
_TRACER_PROVIDER: TracerProvider | None = None
_REDIS_INSTRUMENTED = False
_INSTRUMENTED_SQLALCHEMY_ENGINE_IDS: set[int] = set()


def setup_tracing(app: FastAPI) -> None:
    if not SETTINGS.TRACING_ENABLED:
        return

    provider = _get_or_create_tracer_provider()
    # The SDK wraps user middleware, so request context can read the server span.
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls=TRACING_EXCLUDED_URLS,
        exclude_spans=["receive", "send"],
    )
    _instrument_redis(provider)


def instrument_sqlalchemy_engine(engine: AsyncEngine) -> None:
    if not SETTINGS.TRACING_ENABLED:
        return

    engine_id = id(engine.sync_engine)
    if engine_id in _INSTRUMENTED_SQLALCHEMY_ENGINE_IDS:
        return

    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        tracer_provider=_get_or_create_tracer_provider(),
    )
    _INSTRUMENTED_SQLALCHEMY_ENGINE_IDS.add(engine_id)


def _get_or_create_tracer_provider() -> TracerProvider:
    global _TRACER_PROVIDER
    if _TRACER_PROVIDER is not None:
        return _TRACER_PROVIDER

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": SETTINGS.OTEL_SERVICE_NAME,
                "service.version": "0.1.0",
                "deployment.environment": SETTINGS.APP_ENV,
            }
        ),
        sampler=ParentBased(root=TraceIdRatioBased(_trace_sample_ratio())),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=SETTINGS.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=SETTINGS.OTEL_EXPORTER_OTLP_INSECURE,
                timeout=SETTINGS.OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS,
            )
        )
    )
    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER = provider
    return provider


def _instrument_redis(provider: TracerProvider) -> None:
    global _REDIS_INSTRUMENTED
    if _REDIS_INSTRUMENTED:
        return
    RedisInstrumentor().instrument(tracer_provider=provider)
    _REDIS_INSTRUMENTED = True


def _trace_sample_ratio() -> float:
    return min(max(SETTINGS.OTEL_TRACE_SAMPLE_RATIO, 0.0), 1.0)
