from __future__ import annotations

import os

from ..providers import ProviderResult


class ExaProvider:
    name = "exa"

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Exa client."""
        if self._client is None:
            from exa_py import Exa

            api_key = os.environ.get("EXA_API_KEY", "")
            self._client = Exa(api_key=api_key)
        return self._client

    def search(self, query: str, **kwargs: object) -> ProviderResult:
        try:
            response = self.client.search_and_contents(
                query,
                type="auto",
                num_results=5,
                text={"max_characters": 1000},
                highlights=True,
            )

            sources: list[dict] = []
            content_parts: list[str] = []

            for result in response.results:
                title = getattr(result, "title", "")
                url = getattr(result, "url", "")
                highlights = getattr(result, "highlights", [])
                text = getattr(result, "text", "")

                sources.append({"title": title, "url": url})

                if highlights:
                    content_parts.append(
                        f"**{title}** ({url})\n" + "\n".join(highlights)
                    )
                elif text:
                    content_parts.append(f"**{title}** ({url})\n{text[:500]}")

            return ProviderResult(
                provider=self.name,
                query=query,
                content="\n\n".join(content_parts),
                sources=sources,
            )
        except Exception as e:
            return ProviderResult(
                provider=self.name,
                query=query,
                content="",
                error=str(e),
            )
