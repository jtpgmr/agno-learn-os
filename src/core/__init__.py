from agno.models.base import Model
from agno.learn import LearningMode, LearningMachine, UserProfileConfig
from textwrap import dedent
from agno.memory import MemoryManager
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


def getResponseModel(
    settings: AppSettings | None = None, model_name: str | None = None
) -> OpenAILike:
    ai_settings: AIModelSettings = (settings or getSettings()).ai

    return OpenAILike(
        id=model_name or ai_settings.response_model,
        api_key=ai_settings.api_key.get_secret_value(),
        provider=ai_settings.model_provider,
        base_url=ai_settings.provider_base_url,
    )


def getEmbeddingModel(settings: AppSettings | None = None) -> OpenAILikeEmbedder:
    ai_settings: AIModelSettings = (settings or getSettings()).ai

    return OpenAILikeEmbedder(
        id=ai_settings.embedding_model,
        api_key=ai_settings.api_key.get_secret_value(),
        base_url=ai_settings.provider_base_url,
    )


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
        table_name=table_name,
        schema=schema_name,
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
                db_url=db.db_url or settings.db.dsn,
                table_name=db.knowledge_table_name,
                embedding_model=embedding_model,
            ),
        )

    db = getDatabase(settings.db.dsn)
    return Knowledge(
        contents_db=db,
        vector_db=getVectorStore(
            db_url=db.db_url or settings.db.dsn,
            table_name=db.knowledge_table_name,
            embedding_model=embedding_model,
        ),
    )


_MEMORY_CAPTURE = dedent("""
    Capture durable engineering context that should change how future runs behave:

    - Stack, framework versions, and tooling preferences
    - Project, repository, and service names, and what each one is
    - Architectural decisions already made and the reason behind them
    - Conventions the user has stated or corrected you on
    - Recurring constraints (deployment target, provider, data residency)

    Prefer updating an existing memory over creating a near-duplicate one.
""")

_MEMORY_EXCLUSIONS = dedent("""
    Never capture: secrets, tokens, connection strings, or credentials of any kind;
    transient task state ("currently debugging X"); restatements of the current
    question; anything derivable from the code in context; speculative plans the
    user has not committed to.
""")


def getMemoryManager(
    *,
    db: AsyncPostgresDb | None = None,
    settings: AppSettings | None = None,
    model: OpenAILike | None = None,
) -> MemoryManager:
    """Return a MemoryManager writing to the configured memory table."""
    settings = settings or getSettings()
    db = db or getDatabase(settings.db.dsn)

    return MemoryManager(
        db=db,
        model=model or getResponseModel(settings, settings.ai.extraction_model),
        memory_capture_instructions=_MEMORY_CAPTURE,
        additional_instructions=_MEMORY_EXCLUSIONS,
    )


def getLearningMachine(
    *,
    settings: AppSettings | None = None,
    db: AsyncPostgresDb | None = None,
    profile_mode: LearningMode | None = LearningMode.ALWAYS,
    entity_mode: LearningMode | None = None,
    learned_knowledge_mode: LearningMode | None = LearningMode.AGENTIC,
    enable_planning: bool = False,
    namespace: str | None = None,
    knowledge: Knowledge | None = None,
    model: Model | None = None,
) -> LearningMachine:
    """Assemble a LearningMachine from the four opt-in stores.

    ``None`` for a mode leaves that store off entirely — no extractor call,
    no tools, no context injection.

    Modes:
        ALWAYS      extractor runs every turn, on the response path
        BACKGROUND  extractor runs off the response path (no added latency)
        AGENTIC     agent gets write tools and decides when to use them
        PROPOSE     agent proposes, run pauses for human confirmation

    Args:
        profile_mode: Single-record "who am I talking to" store.
        entity_mode: Entity/relationship graph. Searched, not injected.
        learned_knowledge_mode: Agent-written learnings. ``AGENTIC`` grants
            ``save_learning`` and ``search_learnings``.
        enable_planning: Have session context track goal/plan/progress.
        namespace: Isolation key for entity memory (per tenant or domain).
        knowledge: Vector store backing learned knowledge.
        model: Extractor model; defaults to the cheap extraction model.
    """
    settings = settings or getSettings()
    db = db or getDatabase(settings.db.dsn)
    extraction_model = model or getResponseModel(settings, settings.ai.extraction_model)

    return LearningMachine(
        db=db,
        model=extraction_model,
        knowledge=knowledge or getKnowledge(),
        user_profile=UserProfileConfig(mode=profile_mode) if profile_mode else None,
        # entity_memory=(
        #     EntityMemoryConfig(mode=entity_mode, namespace=namespace) if entity_mode else None
        # ),
        # session_context=(
        #     SessionContextConfig(mode=LearningMode.ALWAYS, enable_planning=True)
        #     if enable_planning
        #     else None
        # ),
        # learned_knowledge=(
        #     LearnedKnowledgeConfig(mode=learned_knowledge_mode) if learned_knowledge_mode else None
        # ),
    )
