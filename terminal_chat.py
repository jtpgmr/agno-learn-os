from src.models.agent_spec import AgentSpecTool
import asyncio
from uuid import uuid4

from src.agents.verifier import buildCodeVerifier

# from src.agents.tech_scout import buildTechScout
from src.core import getSettings, initializeAgnoSchema
from src.runtimes.cli import terminalChatSession
from src.tools import DevToTools, getPresetMcpServerUrls, getPresetStdioMcpServers
from agno.tools.mcp import StreamableHTTPClientParams, MCPTools, SSEClientParams

from mcp import StdioServerParameters


async def main() -> str:
    settings = getSettings()
    session_id: str = str(settings.feature_test.session_id or uuid4())
    user_id: str = str(settings.feature_test.user_id or uuid4())

    await initializeAgnoSchema()

    server_params: list[StdioServerParameters] = [
        # *getPresetMcpServerUrls(), # StreamableHTTPClientParams giving issues
        # *getPresetStdioMcpServers(settings),
    ]

    mcp_tools: list[AgentSpecTool] = []

    for params in server_params:
        mcp_tools.append(
            AgentSpecTool(
                toolkit=MCPTools(
                    server_params=params,
                )
            )
        )

    code_verifier = buildCodeVerifier(settings, tool_spec=mcp_tools)

    print("The current session id is:\t", session_id, "\n")

    # raise Exception(user_id, session_id, code_verifier.tools)

    return await terminalChatSession(code_verifier, user_id=user_id, session_id=session_id)


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTerminal chat session ended.")
