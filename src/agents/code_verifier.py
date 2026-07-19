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

AGENT_NAME = "Code Verifier"


def getPresetStdioMcpServers(settings: AppSettings) -> list[StdioServerParameters]:
    _STDIO_MCP_SERVERS: dict[str, list[StdioMcpSetupOptions]] = {  # noqa N806
        "uvx": [
            StdioMcpSetupOptions(
                mcp="mcp-server-docker",
                env={"DOCKER_HOST": docker_host} if (docker_host := settings.docker_host) else None,
            ),
            # StdioMcpSetupOptions(mcp="docker-mcp"),
            StdioMcpSetupOptions(mcp="markitdown-mcp"),
            # StdioMcpSetupOptions(mcp="mcp-pandoc", args=["--with", "pypandoc-binary"]),
        ]
    }

    server_params_list: list[StdioServerParameters] = []

    for command in AVAILABLE_STDIO_COMMANDS:
        mcp_options = _STDIO_MCP_SERVERS.get(command)

        if mcp_options:
            for options in mcp_options:
                server_params_list.append(
                    StdioServerParameters(
                        command=command,
                        args=[
                            *(options.args or []),
                            options.mcp,
                        ],  # unpack each string in the list with *
                        env=options.env,
                    )
                )

    return server_params_list


def buildCodeVerifier(settings: AppSettings, *, session_id: str | None = None) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=dedent("""
            You verify code and software.
            Ensure the docker sandbox stays clean after executing and testing of containers. Do not leave lingering servers running and unneededed images left in the sandbox.
        """),
        instructions=[
            dedent("""

        """)
        ],
    )

    tools_spec: list[AgentSpecTool] = [
        AgentSpecTool(
            toolkit=ReasoningTools(
                #     instructions=dedent(f"""
                # """),
                #     add_instructions=True,
            )
        ),
    ]

    server_params_list: list[StdioServerParameters] = getPresetStdioMcpServers(settings)

    if server_params_list:
        tools_spec.extend(
            [
                AgentSpecTool(toolkit=MCPTools(server_params=server_params, transport="stdio"))
                for server_params in server_params_list
            ]
        )

    if settings.tools.github_access_token and (
        gh_token := settings.tools.github_access_token.get_secret_value()
    ):
        tools_spec.append(AgentSpecTool(toolkit=GithubTools(access_token=gh_token)))

    if settings.tools.exa_api_key and (exa_token := settings.tools.exa_api_key.get_secret_value()):
        tools_spec.append(AgentSpecTool(toolkit=ExaTools(api_key=exa_token)))

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
