from dataclasses import asdict

from agno.agent import Agent
from agno.db.postgres.async_postgres import AsyncPostgresDb
from agno.models.base import Model

from src.models.agent_spec import AgentSpec


def buildAgent(
    agent_spec: AgentSpec,
    *,
    response_model: Model | None = None,
    db: AsyncPostgresDb | None = None,
):
    if not agent_spec.use_db:
        db = None

    # print(agent_spec.toolkit)
    # print(list(map(lambda x: x.async_functions, agent_spec.toolkit.tools)))

    # raise Exception()

    return Agent(
        **asdict(agent_spec.history) if agent_spec.history else {},
        **asdict(agent_spec.session) if agent_spec.session else {},
        **asdict(agent_spec.options) if agent_spec.options else {},
        **asdict(agent_spec.metadata),
        **asdict(agent_spec.toolkit.settings),
        tools=agent_spec.toolkit.tools,
        skills=agent_spec.skills,
        db=db,
        model=response_model,
    )
