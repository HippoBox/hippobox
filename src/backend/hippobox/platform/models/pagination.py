"""Shared offset-list response; domains own filtering and ordering."""

from typing import Generic, TypeVar

from pydantic import BaseModel

Item = TypeVar("Item")


class PageResponse(BaseModel, Generic[Item]):
    items: list[Item]
    total: int
    page: int
    page_size: int
