from textwrap import dedent

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools
from agno.tools.workspace import Workspace as WorkspaceTools

from src.core import getResponseModel
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)
from src.utils import getSessionWorkspace
from src.utils.agent import buildAgent

AGENT_NAME = "Analyst"


def buildAnalyst(settings: AppSettings, *, session_id: str | None = None) -> Agent:
    metadata = AgentSpecMetadata(
        name="Analyst",
        role=dedent("""
            Consumes structured data from Scout agents and synthesizes it into cohesive, 
            well-reasoned judgments. Strictly isolated from raw retrieval tools.
        """),
        instructions=[
            dedent("""
            You are the Analyst. You do not gather information; you make sense of it.
            You will receive structured SOP artifacts and raw JSON/Markdown data gathered by the Scouts.

            Your task is to:
            1. Cross-reference the provided data points.
            2. Identify patterns, thematic overlaps, and distinct technical approaches.
            3. Synthesize the findings into a structured judgment, report, or architectural recommendation.
            
            Never guess or hallucinate external facts. If the Scout's data is insufficient to form a 
            conclusion, explicitly flag the data gap in your output and request a follow-up retrieval cycle.
            Rely purely on the context provided to you.
            """)
        ],
    )

    # Note: Analyst intentionally lacks search tools to prevent context pollution.
    tools_spec = [
        AgentSpecTool(
            toolkit=ReasoningTools(
                instructions=dedent("""
                1. Map the arguments: What are the main points supported by the data?
                2. Weigh the evidence: Does the provided metadata indicate high or low confidence?
                3. Structure the output: Group findings logically, not chronologically.
                """),
                add_instructions=True,
            )
        ),
    ]

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
