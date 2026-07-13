import asyncio
from uuid import uuid4

from agno.os import AgentOS, app

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

    agent_os = buildAgentOS([agent], db=db)

    agno_os_app: app.FastAPI = agent_os.get_app()

    try:
        agent_os.serve(agno_os_app)
        # agent_os.serve("main.testAgentOSSession:app", reload=True)
    except Exception as err:
        raise err


test_settings = getSettings()
test_db = getDatabase(db_url=test_settings.db.dsn, create_schema=True)

test_session_id: str = str(test_settings.feature_test.session_id or uuid4())

test_agent = buildSoftwareNewsFinder(test_settings, test_session_id)

test_agent_os: AgentOS = buildAgentOS([test_agent], db=test_db)

test_agno_os_app: app.FastAPI = test_agent_os.get_app()


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(testTerminalChatSession())
    except KeyboardInterrupt:
        print("\nTerminal chat session ended.")

    print(session)
    # testAgentOSSession()

    # need string import path of app to trigger reload
    # test_agent_os.serve("test:test_agno_os_app", reload=True)
