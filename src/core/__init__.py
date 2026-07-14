from functools import lru_cache

from agno.db.postgres import AsyncPostgresDb
from agno.knowledge.embedder.openai_like import OpenAILikeEmbedder
from agno.models.openai import OpenAILike
from agno.tools.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from .settings import AIModelSettings, AppSettings

DEFAULT_SCHEMA_AI = "agno"


@lru_cache
def getSettings() -> AppSettings:
    return AppSettings()


@lru_cache
def getDatabase(
    db_url: str,
    *,
    schema_name: str = DEFAULT_SCHEMA_AI,
    create_schema: bool = False,
    session_table: str | None = None,
    memory_table: str | None = None,
    **kwargs,
) -> AsyncPostgresDb:
    return AsyncPostgresDb(
        db_url=db_url,
        db_schema=schema_name,
        create_schema=create_schema,
        session_table=session_table,
        memory_table=memory_table,
        **kwargs,
    )


async def initializeAgnoSchema(
    *,
    db: AsyncPostgresDb | None = None,
    settings: AppSettings | None = None,
    schema_name: str = DEFAULT_SCHEMA_AI,
    memory_table: str | None = None,
    session_table: str | None = None,
    metrics_table: str | None = None,
    knowledge_table: str | None = None,
    culture_table: str | None = None,
    traces_table: str | None = None,
    spans_table: str | None = None,
    versions_table: str | None = None,
    learnings_table: str | None = None,
    schedules_table: str | None = None,
    schedule_runs_table: str | None = None,
    approvals_table: str | None = None,
    auth_tokens_table: str | None = None,
):
    settings = settings or getSettings()

    db = db or getDatabase(
        settings.db.dsn,
        create_schema=True,
        schema_name=schema_name,
        memory_table=memory_table,
        session_table=session_table,
        metrics_table=metrics_table,
        knowledge_table=knowledge_table,
        culture_table=culture_table,
        traces_table=traces_table,
        spans_table=spans_table,
        versions_table=versions_table,
        learnings_table=learnings_table,
        schedules_table=schedules_table,
        schedule_runs_table=schedule_runs_table,
        approvals_table=approvals_table,
        auth_tokens_table=auth_tokens_table,
    )

    await db._create_all_tables()


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
def getVectorStore(
    db_url: str,
    table_name: str,
    *,
    schema_name: str = DEFAULT_SCHEMA_AI,
    search_type: SearchType = SearchType.hybrid,
    embedding_model: OpenAILikeEmbedder | None = None,
    **kwargs,
) -> PgVector:
    return PgVector(
        db_url=db_url,
        schema=schema_name,
        table_name=table_name,
        search_type=search_type,
        embedder=embedding_model or getEmbeddingModel(),
        **kwargs,
    )


@lru_cache
def getKnowledge(
    *,
    db: AsyncPostgresDb | None = None,
    settings: AppSettings | None = None,
    embedding_model: OpenAILikeEmbedder | None = None,
) -> Knowledge:
    settings = settings or getSettings()
    if not db and not settings:
        raise ValueError("AppSettings or DB class instance is needed to create knowledge base")

    if db:
        return Knowledge(
            contents_db=db,
            vector_db=getVectorStore(
                db.db_url, db.knowledge_table_name, embedding_model=embedding_model
            ),
        )

    db = getDatabase(settings.db.dsn)
    return Knowledge(
        contents_db=db,
        vector_db=getVectorStore(
            db.db_url, db.knowledge_table_name, embedding_model=embedding_model
        ),
    )
