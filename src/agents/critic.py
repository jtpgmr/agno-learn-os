from src.utils import getSessionWorkspace
from agno.tools.workspace import Workspace as WorkspaceTools
from agno.tools.mcp import MCPTools
from src.tools.mcp import StdioMcpSetupOptions, AVAILABLE_STDIO_COMMANDS
from mcp import StdioServerParameters
from textwrap import dedent

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.tools.github import GithubTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.reasoning import ReasoningTools

from src.core import getResponseModel
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)
from src.utils.agent import buildAgent

AGENT_NAME = "Adversarial Critic"


def buildCritic(settings: AppSettings) -> Agent:
    metadata = AgentSpecMetadata(
        name="Adversary",
        role=dedent("""
            Relentlessly attacks drafts and synthesized outputs to expose blind spots, 
            logical fallacies, and structural weaknesses via verbal self-feedback loops.
        """),
        instructions=[
            dedent("""
            You are the Adversarial Critic. Your sole purpose is to tear down the Analyst's draft 
            and expose its weaknesses. You do not write the final product; you grade it.

            For every draft provided:
            1. Attack the logic: Are there jumps in reasoning?
            2. Attack the scope: Did the Analyst answer the original prompt, or drift?
            3. Attack the clarity: Is the structure confusing or redundant?
            4. Provide actionable self-refinement feedback. 

            Do not be polite. Be objective, precise, and highly critical. If the draft is flawless, 
            you must actively search for edge cases where the proposed solution or synthesis breaks down.
            """)
        ],
    )

    tools_spec = [
        AgentSpecTool(
            toolkit=ReasoningTools(
                instructions=dedent("""
                Apply the Reflexion methodology:
                1. Observe the draft's claims.
                2. Hypothesize scenarios where the claims fail.
                3. Output a strict bulleted list of necessary revisions.
                """),
                add_instructions=True,
            )
        )
    ]

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tools_spec),
        history=None,
    )
    return buildAgent(agent_spec, response_model=getResponseModel(settings))
