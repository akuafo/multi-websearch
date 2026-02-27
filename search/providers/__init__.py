from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ProviderResult:
    provider: str
    query: str
    content: str
    sources: list[dict] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class SearchProvider(Protocol):
    name: str

    def search(self, query: str, **kwargs: object) -> ProviderResult: ...
