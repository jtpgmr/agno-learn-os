from uuid import uuid4

from agno.agent import Agent

EXIT_COMMANDS = {"exit", "quit"}


async def terminalChatSession(
    agent: Agent, *, user_id: str | None = None, session_id: str | None = None
) -> str:
    session_id = session_id or str(uuid4())
    print(f"Session started: {session_id}  (type {EXIT_COMMANDS} or press 'Ctrl+C' to end)\n")

    while True:
        try:
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
            break
        finally:
            print(
                f"\nEnding chat. Resume this conversation using the session ID {session_id}",
            )

    return session_id
