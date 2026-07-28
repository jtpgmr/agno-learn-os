from agno.tools.python import PythonTools
from agno.tools.calculator import CalculatorTools
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
    AgentSpecSessionSettings,
)
from src.utils.agent import buildAgent

AGENT_NAME = "Verifier"
PRESET_TOOL_SPEC: list[AgentSpecTool] = [
    AgentSpecTool(toolkit=PythonTools()),
    AgentSpecTool(toolkit=CalculatorTools()),
    AgentSpecTool(toolkit=DuckDuckGoTools()),
]


def buildCodeVerifier(
    settings: AppSettings,
    *,
    session_id: str | None = None,
    tool_spec: list[AgentSpecTool] | None = None,
    apply_preset_tool_spec: bool | None = True,
) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=dedent("""
            Grounds claims in objective reality by executing code, running calculations, 
            or re-querying precise data points. Employs tool-grounded verification.
        """),
        instructions=[
            dedent("""
                You are the Verifier. You do not judge the quality of the argument (that is the Critic's job);
                you check the ground truth of the facts, calculations, and code.

                When reviewing a claim:
                1. Distill the claim into a testable hypothesis.
                2. Write and execute Python code, or use the Calculator, to verify any math or logic.
                3. Use Exa or DuckDuckGo strictly for exact-match fact checking (e.g., "Is X actually deprecated?").
                4. Return a strict TRUE/FALSE/PARTIAL status for each claim, accompanied by the tool output 
                that proves your verdict.

                Do not rely on your internal LLM weights. If you cannot verify it with a tool, mark it UNVERIFIED.
        """)
        ],
    )

    tool_spec: list[AgentSpecTool] = tool_spec or []

    if apply_preset_tool_spec:
        tool_spec.extend(PRESET_TOOL_SPEC)

    if settings.ai.session_data_path:
        workspace: WorkspaceTools = getSessionWorkspace(
            settings.ai.session_data_path,
            session_id=session_id,
        )
        tool_spec.append(AgentSpecTool(toolkit=workspace))

    if settings.tools.github_access_token and (
        gh_token := settings.tools.github_access_token.get_secret_value()
    ):
        tool_spec.append(AgentSpecTool(toolkit=GithubTools(access_token=gh_token)))

    if settings.tools.exa_api_key and (exa_token := settings.tools.exa_api_key.get_secret_value()):
        tool_spec.append(AgentSpecTool(toolkit=ExaTools(api_key=exa_token)))

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tool_spec),
        history=None,
        session=AgentSpecSessionSettings(enable_session_summaries=False),
    )

    return buildAgent(agent_spec, response_model=getResponseModel(settings))
