from functools import lru_cache
from uuid import uuid4

from agno.agent import Agent
from agno.db.postgres import AsyncPostgresDb
from agno.knowledge.embedder.openai_like import OpenAILikeEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.models.openai import OpenAILike
from agno.vectordb.pgvector import PgVector, SearchType

from .settings import AIModelSettings, AppSettings


@lru_cache
def getSettings() -> AppSettings:
    return AppSettings()  # type: ignore[call-arg]


@lru_cache
def getDatabase(
    db_url: str,
    *,
    schema_name: str | None = None,
    table_name: str | None = None,
    memory_table: str | None = None,
    session_table: str | None = None,
    create_schema: bool = False,
    **kwargs,
) -> AsyncPostgresDb:
    return AsyncPostgresDb(
        db_url=db_url,
        db_schema=schema_name,
        knowledge_table=table_name,
        memory_table=memory_table,
        session_table=session_table,
        create_schema=create_schema,
        **kwargs,
    )


@lru_cache
def getVectorStore(
    db_url: str,
    table_name: str,
    embedding_model: OpenAILikeEmbedder,
    schema_name: str = "agno",
    search_type: SearchType = SearchType.hybrid,
    **kwargs,
) -> PgVector:
    return PgVector(
        db_url=db_url,
        schema=schema_name,
        table_name=table_name,
        search_type=search_type,
        embedder=embedding_model,
        **kwargs,
    )


@lru_cache
def getResponseModel() -> OpenAILike:
    ai_settings: AIModelSettings = getSettings().ai

    return OpenAILike(
        id=ai_settings.response_model,
        api_key=ai_settings.api_key.get_secret_value(),
        provider=ai_settings.model_provider,
        base_url=ai_settings.provider_base_url,
    )


@lru_cache
def getEmbeddingModel() -> OpenAILikeEmbedder:
    ai_settings: AIModelSettings = getSettings().ai

    return OpenAILikeEmbedder(
        id=ai_settings.embedding_model,
        api_key=ai_settings.api_key.get_secret_value(),
        base_url=ai_settings.provider_base_url,
    )


@lru_cache
def getKnowledge() -> Knowledge:
    return Knowledge(
        # name="",
        # description="",
        contents_db=getDatabase(),
        vector_db=getVectorStore(),
    )


async def chatWithAgent(agent: Agent, *, user_id: str | None = None, session_id: str | None = None):
    if not session_id:
        session_id = str(uuid4())
    while True:
        prompt = input("\nYou: ")

        if prompt.lower() in {"exit", "quit"}:
            break

        await agent.aprint_response(
            prompt, user_id=user_id, session_id=session_id, stream=True, markdown=True
        )
