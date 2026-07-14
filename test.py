import asyncio
from uuid import uuid4

from agno.os import AgentOS
from fastapi import FastAPI

from src.agents.software_news_finder import buildSoftwareNewsFinder
from src.core import getDatabase, getSettings
from src.runtimes.agent_os import buildAgentOS
from src.runtimes.cli import terminalChatSession


async def testTerminalChatSession() -> str:
    settings = getSettings()

    session_id: str = str(settings.feature_test.session_id or uuid4())

    print("The current session id is:\t", session_id)

    agent = buildSoftwareNewsFinder(settings, session_id)

    return await terminalChatSession(agent, session_id=session_id)


def testAgentOSSession():
    settings = getSettings()
    db = getDatabase(db_url=settings.db.dsn, create_schema=True)

    session_id: str = str(settings.feature_test.session_id or uuid4())

    print("The current session id is:\t", session_id)

    agent = buildSoftwareNewsFinder(settings, session_id)

    agent_os: AgentOS = buildAgentOS([agent], db=db)

    agno_os_app: FastAPI = agent_os.get_app()

    try:
        agent_os.serve(agno_os_app)
    except Exception as err:
        raise err


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(testTerminalChatSession())
    except KeyboardInterrupt:
        print("\nTerminal chat session ended.")
