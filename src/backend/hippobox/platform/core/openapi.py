"""Expose transport contracts that do not use ordinary JSON response models."""

from typing import Any, Literal

from fastapi import FastAPI, status
from pydantic import BaseModel

from hippobox.platform.core.realtime.contracts import RealtimeStreamEvent
from hippobox.platform.core.realtime.events import RealtimeEvent


class InternalErrorResponse(BaseModel):
    error: Literal["INTERNAL_ERROR"]
    message: str


def register_openapi_contracts(app: FastAPI) -> None:
    original_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = original_openapi()
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        for model in (RealtimeEvent, RealtimeStreamEvent, InternalErrorResponse):
            model_schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}", mode="serialization"
            )
            for name, definition in model_schema.pop("$defs", {}).items():
                schemas.setdefault(name, definition)
            schemas[model.__name__] = model_schema

        # Unexpected failures keep the existing top-level error envelope. A domain
        # 500 and an unexpected 500 must both remain visible in the same response.
        internal_ref = {"$ref": "#/components/schemas/InternalErrorResponse"}
        for path in schema["paths"].values():
            for method, operation in path.items():
                if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                response = operation["responses"].setdefault(
                    str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                    {"description": "Unexpected server error"},
                )
                content = response.setdefault("content", {}).setdefault("application/json", {})
                previous = content.get("schema")
                content["schema"] = (
                    {"anyOf": [previous, internal_ref]} if previous else internal_ref
                )
        return schema

    app.openapi = openapi
