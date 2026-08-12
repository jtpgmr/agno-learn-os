from agno.utils.pprint import pprint_run_response
from agno.models.response import ToolExecution
from agno.tools import Toolkit
from agno.run.agent import RunOutput
from uuid import uuid4

from agno.agent import Agent

EXIT_COMMANDS: set[str] = {"exit", "quit"}
MAX_PROMPT_LENGTH: int = 250_000


async def terminalChatSession(
    agent: Agent,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    # department_code: str, email: str
) -> str:
    session_id = session_id or str(uuid4())
    user_id = user_id or str(uuid4())
    print(
        f"\nSession {session_id} started as user {user_id} (type {EXIT_COMMANDS} or press 'Ctrl+C' to end)\n"
    )
    try:
        while True:
            prompt: str = input("\nYou: ")

            # santize prompt
            prompt = (
                prompt.strip().encode(encoding="utf-8", errors="replace").decode(encoding="utf-8")
            )

            prompt = min(prompt, prompt[:MAX_PROMPT_LENGTH])

            if not prompt:
                continue

            if prompt.lower() in EXIT_COMMANDS:
                break

            # response = await agent.aprint_response(
            #     prompt, user_id=user_id, session_id=session_id, stream=True, markdown=True
            # )

            output: RunOutput = await agent.arun(prompt, user_id=user_id, session_id=session_id)

            while output.is_paused:
                for t in output.tools_requiring_confirmation:
                    t: ToolExecution
                    ans = input(f"Run {t.tool_name}({t.tool_args})? [y/N] ")
                    t.confirmed = ans.strip().lower() == "y"
                    if not t.confirmed:
                        t.tool_call_error = "User declined. Use another approach."
                output = await agent.acontinue_run(
                    run_id=output.run_id,
                    updated_tools=output.tools,
                    session_id=session_id,
                    user_id=user_id,
                )

            pprint_run_response(output, markdown=True)

    except KeyboardInterrupt:
        pass
    finally:
        print(
            f"\nEnding chat. Resume this conversation using the session ID {session_id}",
        )

    return session_id
