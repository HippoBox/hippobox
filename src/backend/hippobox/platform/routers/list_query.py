"""Reusable scalar query annotations, preserving each route's OpenAPI contract."""

from typing import Annotated

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_SEARCH_LENGTH = 200

PageQuery = Annotated[int, Query(ge=1)]
PageSizeQuery = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
SearchQuery = Annotated[str, Query(max_length=MAX_SEARCH_LENGTH)]
