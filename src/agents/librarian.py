from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import AsyncPostgresDb
from agno.tools.knowledge import KnowledgeTools

from src.core import getResponseModel, getKnowledge
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)
from src.utils.agent import buildAgent

AGENT_NAME = "Librarian"


def buildTechScout(settings: AppSettings, db: AsyncPostgresDb) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=dedent("""
        """),
        instructions=[
            dedent("""
        """)
        ],
    )

    tools_spec: list[AgentSpecTool] = []

    try:
        knowledge = getKnowledge(db=db)

        tools_spec.append(AgentSpecTool(toolkit=KnowledgeTools(knowledge=knowledge)))
    except ValueError:
        pass

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tools_spec),
        history=None,
    )

    return buildAgent(agent_spec, response_model=getResponseModel(settings))
