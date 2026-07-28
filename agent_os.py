"""Entrypoint wrapper for the `agentos` compose service.

Runs `testAgentOSSession()` from test.py inside the AgentOS container.
Using a thin wrapper (instead of `python -c "from test import ..."`) avoids
top-level import side effects in test.py and gives a clear, debuggable command.

The actual HTTP bind host/port are controlled by the compose environment:
    AGENT_OS_HOST=0.0.0.0   (agno serve() defaults to localhost -> unreachable)
    AGENT_OS_PORT=7777
These are read by agno.agent_os.AgentOS.serve() (v2.5.8+), so no code changes
are needed here.
"""

from uuid import uuid4

from agno.os import AgentOS
from fastapi import FastAPI

from src.agents.verifier import buildCodeVerifier
from src.core import getDatabase, getSettings
from src.runtimes.agent_os import buildAgentOS


def main():
    settings = getSettings()
    db = getDatabase(db_url=settings.db.dsn, create_schema=True)

    session_id: str = str(settings.feature_test.session_id or uuid4())

    print("The current session id is:\t", session_id)

    agent = buildCodeVerifier(settings, session_id=session_id)

    agent_os: AgentOS = buildAgentOS([agent], db=db)

    agno_os_app: FastAPI = agent_os.get_app()

    try:
        agent_os.serve(agno_os_app)
    except Exception as err:
        raise err


if __name__ == "__main__":
    main()
