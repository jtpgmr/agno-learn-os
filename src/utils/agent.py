from src.core import getMemoryManager, getLearningMachine
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

    # Memory and learning both need a db to persist to.
    memory_manager = None
    learning = None

    if (
        db
        and agent_spec.memory
        and (agent_spec.memory.enable_user_memories or agent_spec.memory.enable_agentic_memory)
    ):
        memory_manager = getMemoryManager(db=db)

    if db and (spec := agent_spec.learning):
        learning = getLearningMachine(
            profile_mode=spec.profile_mode,
            entity_mode=spec.entity_mode,
            learned_knowledge_mode=spec.learned_knowledge_mode,
            enable_planning=spec.enable_planning,
            namespace=spec.namespace,
        )

    # print(agent_spec.toolkit)
    # print(list(map(lambda x: x.async_functions, agent_spec.toolkit.tools)))

    # raise Exception()

    return Agent(
        **asdict(agent_spec.history) if agent_spec.history else {},
        **asdict(agent_spec.session) if agent_spec.session else {},
        **asdict(agent_spec.options) if agent_spec.options else {},
        **asdict(agent_spec.memory) if agent_spec.memory else {},
        **asdict(agent_spec.metadata),
        **asdict(agent_spec.toolkit.settings),
        tools=agent_spec.toolkit.tools,
        skills=agent_spec.skills,
        db=db,
        model=response_model,
        memory_manager=memory_manager,
        learning=learning,
    )
