"""Async client for the dev.to (Forem) public API.

Owns the dev.to API contract: endpoints, params, and validation of responses
into typed pydantic models. No auth required. The agent-facing toolkit
(`src.agents.tools.devto`) is a thin wrapper over this client.
"""

from typing import Any

from httpx import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import AsyncHttpClient

_API_BASE = "https://dev.to/api"


def tagsToList(tags: object) -> list[str]:
    # dev.to returns tags as a list on the list endpoint (tag_list) and as a
    # comma-joined string on the detail endpoint (tags).
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    return []


class DevToArticle(BaseModel):
    """A dev.to article summary from the list endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    url: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list, alias="tag_list")
    published: str | None = Field(None, alias="readable_publish_date")
    reading_minutes: int | None = Field(None, alias="reading_time_minutes")

    @field_validator("tags", mode="before")
    @classmethod
    def _tagsToList(cls, value: object) -> list[str]:
        return tagsToList(value)


class DevToArticleDetail(BaseModel):
    """A single dev.to article including its markdown body."""

    model_config = ConfigDict(extra="ignore")

    title: str
    url: str
    tags: list[str] = Field(default_factory=list)
    reactions: int = Field(0, alias="positive_reactions_count")
    comments: int = Field(0, alias="comments_count")
    body_markdown: str = ""

    @field_validator("tags", mode="before")
    @classmethod
    def _tagsToList(cls, value: object) -> list[str]:
        return tagsToList(value)


class DevToClient:
    """Typed access to the dev.to public API.

    Args:
        http: Optional shared HTTP client for pooling/testing. When omitted,
            each call opens and disposes its own short-lived client.
    """

    def __init__(self, http: AsyncHttpClient | None = None) -> None:
        self._http: AsyncHttpClient = http or AsyncHttpClient(base_url=_API_BASE)

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Response:
        return await self._http.call(endpoint, params=params)

    async def searchArticles(
        self, tag: str, top_days: int = 30, per_page: int = 10
    ) -> list[DevToArticle]:
        """Return the most-reacted articles for a tag over the look-back window."""
        response = await self._get(
            "/articles",
            params={"tag": tag.strip().lower(), "top": top_days, "per_page": per_page},
        )

        data = response.json()
        if not isinstance(data, list):
            raise ValueError("unexpected dev.to response shape (expected a list)")
        return [DevToArticle.model_validate(item) for item in data]

    async def getArticle(self, article_id: int) -> DevToArticleDetail:
        """Return one article including its markdown body."""
        response = await self._get(f"/articles/{article_id}")
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("unexpected dev.to response shape (expected an object)")
        return DevToArticleDetail.model_validate(data)


async def test():
    dtc = DevToClient()

    articles = await dtc.searchArticles(tag="ai")

    article = await dtc.getArticle(articles[0].id)
    print(article)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
