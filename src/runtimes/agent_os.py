from __future__ import annotations

from agno.agent import Agent
from agno.db.postgres import AsyncPostgresDb
from agno.os import AgentOS
from agno.team import Team

from src.core import AppSettings, getDatabase, getSettings


# AgentOS already handles Database `_create_all_tables`
def buildAgentOS(
    agents: list[Agent] | None = None,
    teams: list[Team] | None = None,
    *,
    db: AsyncPostgresDb | None = None,
    settings: AppSettings | None = None,
    os_id: str = "agno-learn-os",
    description: str = "Agno LearnOS",
    tracing: bool = True,
) -> AgentOS:
    if not agents and not teams:
        raise Exception("AgentOS requires at least one Agent or Team to operate.")

    settings = settings or getSettings()
    db = db or getDatabase(db_url=settings.db.dsn, create_schema=True)

    return AgentOS(
        id=os_id,
        description=description,
        agents=agents,  # ty: ignore[invalid-argument-type]
        teams=teams,  # ty: ignore[invalid-argument-type]
        db=db,
        tracing=tracing,
    )
