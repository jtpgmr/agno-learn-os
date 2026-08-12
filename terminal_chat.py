import asyncio
from uuid import uuid4

from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from src.agents.verifier import buildCodeVerifier

# from src.agents.tech_scout import buildTechScout
from src.core import getDatabase, getSettings, initializeAgnoSchema
from src.models.agent_spec import AgentSpecTool
from src.runtimes.cli import terminalChatSession


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

    db = getDatabase(settings.db.dsn)

    code_verifier = buildCodeVerifier(settings, tool_spec=mcp_tools, db=db, session_id=session_id)

    print("The current session id is:\t", session_id, "\n")

    # raise Exception(user_id, session_id, code_verifier.tools)

    return await terminalChatSession(code_verifier, user_id=user_id, session_id=session_id)


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTerminal chat session ended.")
