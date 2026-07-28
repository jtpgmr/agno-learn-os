from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import AsyncPostgresDb
from agno.tools.knowledge import KnowledgeTools
from agno.tools.workspace import Workspace as WorkspaceTools

from src.core import getResponseModel, getKnowledge
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)
from src.utils import getSessionWorkspace
from src.utils.agent import buildAgent


AGENT_NAME = "Scribe"


def buildScribe(settings: AppSettings, db: AsyncPostgresDb) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=dedent("""
            Persists decisions, compresses context, and maintains long-running state 
            to prevent system drift across complex, multi-turn task loops.
        """),
        instructions=[
            dedent("""
                You are the Memory Scribe. Context window is a scarce and expensive resource. 
                Your job is to archive and compress the work of the other agents.

                When provided with a completed iteration or a large conversation thread:
                1. Extract the core decisions made, the rejected paths, and the final state.
                2. Compress this into a dense, highly-structured Markdown summary.
                3. Write this summary to the system's memory files.
                
                Your summaries must allow a new agent waking up from zero context to perfectly 
                understand the current state of the project in under 500 words. Strip all conversational 
                filler and retain only operational data and established facts.
        """)
        ],
    )

    tools_spec: list[AgentSpecTool] = []

    try:
        knowledge = getKnowledge(db=db)

        tools_spec.append(AgentSpecTool(toolkit=KnowledgeTools(knowledge=knowledge)))
    except ValueError:
        pass

    if settings.ai.session_data_path:
        workspace: WorkspaceTools = getSessionWorkspace(
            settings.ai.session_data_path,
            session_id,
            read_only=False,  # set `read_only` to False to allow writing to the workspace folder
        )
        tools_spec.append(AgentSpecTool(toolkit=workspace))

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tools_spec),
        history=None,
    )

    return buildAgent(agent_spec, response_model=getResponseModel(settings))
