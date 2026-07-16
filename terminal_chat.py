import asyncio
from uuid import uuid4

from src.agents.software_news_finder import buildSoftwareNewsFinder
from src.core import getSettings, initializeAgnoSchema
from src.runtimes.cli import terminalChatSession


async def main() -> str:
    settings = getSettings()

    session_id: str = str(settings.feature_test.session_id or uuid4())

    print("The current session id is:\t", session_id, "\n")

    await initializeAgnoSchema()
    agent = buildSoftwareNewsFinder(settings, session_id, read_only=False)

    return await terminalChatSession(agent, session_id=session_id)


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTerminal chat session ended.")
