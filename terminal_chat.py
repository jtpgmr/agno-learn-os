import asyncio
from uuid import uuid4

from src.agents.code_verifier import buildCodeVerifier
from src.agents.tech_scout import buildTechScout
from src.core import getSettings, initializeAgnoSchema
from src.runtimes.cli import terminalChatSession


async def main() -> str:
    settings = getSettings()
    session_id: str = str(settings.feature_test.session_id or uuid4())

    await initializeAgnoSchema()
    tech_scout = buildTechScout(settings)
    code_verifier = buildCodeVerifier(settings, session_id=session_id)

    print("The current session id is:\t", session_id, "\n")

    return await terminalChatSession(code_verifier, session_id=session_id)


if __name__ == "__main__":
    session: str | None = None
    try:
        session = asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTerminal chat session ended.")
