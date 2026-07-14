from uuid import uuid4

from agno.agent import Agent

EXIT_COMMANDS: set[str] = {"exit", "quit"}


async def terminalChatSession(
    agent: Agent, *, user_id: str | None = None, session_id: str | None = None
) -> str:
    session_id = session_id or str(uuid4())
    print(f"\nSession started: {session_id}  (type {EXIT_COMMANDS} or press 'Ctrl+C' to end)\n")
    try:
        while True:
            prompt: str = input("\nYou: ")

            prompt = prompt.strip()

            if not prompt:
                continue

            if prompt.lower() in EXIT_COMMANDS:
                break

            await agent.aprint_response(
                prompt, user_id=user_id, session_id=session_id, stream=True, markdown=True
            )

    except KeyboardInterrupt:
        pass
    finally:
        print(
            f"\nEnding chat. Resume this conversation using the session ID {session_id}",
        )

    return session_id
