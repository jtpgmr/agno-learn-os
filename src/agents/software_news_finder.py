from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.db.postgres.async_postgres import AsyncPostgresDb
from agno.models.base import Model
from agno.skills import Skills
from agno.tools import Toolkit
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.tools.github import GithubTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MultiMCPTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.workspace import Workspace as WorkspaceTools
from mcp import StdioServerParameters

from src.core import AppSettings, getDatabase, getKnowledge, getResponseModel, getSettings
from src.core.utils.agent import excludeTools, getAgentSkills, getSessionWorkspace
from src.tools import DevToTools

# TODO: Tools and features to explore and implement
# from agno.tools.websearch import WebSearchTools
# from agno.tools.youtube import YouTubeTools
# from agno.learn import LearningMachine
# from agno.tools.memory import MemoryTools
# from agno.tools.postgres import PostgresTools
# from agno.memory import MemoryManager, UserMemory
# from agno.tools.email import EmailTools

AVAILABLE_STDIO_COMMANDS = "uvx"
STDIO_MCP_SERVERS = {
    "mcp-server-docker": {
        "args": {},
        "env": {"DOCKER_HOST": docker_host} if (docker_host := getSettings().docker_host) else {},
    },
    "uvx docker-mcp": {},
    "markitdown-mcp": {},
    "mcp-pandoc": {},
}

MCP_URLS: dict[str, str] = {
    "gitmcp.io/docs": "streamable-http",
    "mcp.deepwiki.com/mcp": "streamable-http",
}


def buildSoftwareNewsFinder(
    settings: AppSettings | None = None,
    session_id: str | None = None,
    *,
    db: AsyncPostgresDb | None = None,
    response_model: Model | None = None,
    read_only=True,
    allow_delete=False,
    stale_after_days: int = 365,
) -> Agent:
    settings = settings or getSettings()
    response_model = response_model or getResponseModel()
    skills: Skills | None = None

    # TODO: Implement a better way of administering read/write/delete permissions for each toolkit
    allowed_tools: dict[type[Toolkit], dict[str, Any]] = {}
    tool_call_limit = 30

    docker_mcp = StdioServerParameters(
        command="uvx",
        args=["mcp-server-docker"],
        env={"DOCKER_HOST": settings.docker_host} if settings.docker_host else {},
    )

    # TODO: add a client-side logger for displaying details such as tool configuration
    tools: list[Toolkit] = [
        DuckDuckGoTools(),
        # DevToTools(),
        # HackerNewsTools(),
        ReasoningTools(
            instructions=dedent(f"""
                Before finalizing any research brief, reason step by step and show that reasoning:
                    1. Tier each source. For every source, state the specific claim it supports and its
                    tier: official docs / source repo > vendor engineering blog > community post
                    (dev.to, Hacker News) > generic web. Treat a claim backed only by a low-tier
                    source as unverified, and say so.

                    2. Cross-check. When more than one tool returns results for the same claim, compare
                    them. If they conflict, state the disagreement explicitly and say which source is
                    more authoritative and why — never silently pick one.

                    3. Judge recency. Using the current date in your context, flag any source older than
                    {stale_after_days} days as potentially stale, and note where you lack a recent source.

                    4. Name the gaps. List what the brief still cannot answer from the gathered sources.

                    5. Only then write the brief: ranked by evidence strength, de-duplicated by canonical
                    URL, each item citing its source and tier. Prefer "I could not confirm X" over
                    presenting a weak claim as settled.
            """),
            add_instructions=True,
        ),
        MultiMCPTools(
            urls=["https://gitmcp.io/docs", "https://mcp.deepwiki.com/mcp"],
            urls_transports=["streamable-http", "streamable-http"],
            # commands=["uvx docker-mcp"],
            server_params_list=[docker_mcp],
        ),
    ]

    db = db or getDatabase(db_url=settings.db.dsn, create_schema=True)

    try:
        knowledge = getKnowledge(db=db)

        tools.append(KnowledgeTools(knowledge))
    except ValueError:
        pass

    if settings.tools.exa_api_key:
        tools.append(ExaTools(api_key=settings.tools.exa_api_key.get_secret_value(), all=True))

    if settings.tools.github_access_token:
        allowed_tools[GithubTools] = {
            "access_token": settings.tools.github_access_token.get_secret_value()
        }

    if settings.project_path:
        skills = getAgentSkills(settings.project_path)

    # if settings.docs_path:
    #     tools.append(ArxivTools(all=True, download_dir=settings.docs_path))

    if settings.ai.session_data_path:
        workspace: WorkspaceTools = getSessionWorkspace(
            settings.ai.session_data_path,
            session_id,
            read_only=read_only,  # set `read_only` to False to allow writing to the workspace folder
        )
        tools.append(workspace)

    if allowed_tools:
        for tool_kit, params in allowed_tools.items():
            filtered_toolkit: Toolkit = excludeTools(
                tool_kit=tool_kit(**params), read_only=read_only, allow_delete=allow_delete
            )

            tools.append(filtered_toolkit)

    return Agent(
        name="Feature test agent",
        id="feature-test-agent",
        role="Finds written tutorials and articles on Github and dev.to and engineering blogs.",
        model=response_model,
        tools=tools,
        tool_call_limit=tool_call_limit,
        skills=skills,
        instructions=[
            dedent(f"""
            You are a tech news finder/researcher, powered by the LLM response model {response_model}, whose purpose is to keep me up-to-date with the latest in tech, including
            AI, webdev (across the stack), DevOps, database use and administration, data analysis, robotics, hardware,
            engineering, security, networking, IT and more.

            All news, articles, notes, insight must come from latest/up-to-date resources.

            This includes:
                - Using GitHub (if applicable) to find trending and most latest versions of libraries, projects, SDKs, etc.
                - Use tools like DevToTools for recent articles, discussions and community insight.
                - Use WebSearchTools as fallback for reliable engineering blogs.

            Track searched topics and sources in session state.
            Prefer written tutorials, official docs, engineering blogs, and GitHub repos.
            Avoid repeating links already reviewed in the same session.
            Refer to the database for relevant sessions and contexts, to keep in continuity with prior session messages.

            Write any generated artifacts only inside the provided sandbox directory and use relative paths.
            Never attempt to read, write or modify files outside that directory in any way.

            Always provide references in APA format at the end of responses and confirm the validity and accuracy of
            the data retrieved from sources, before making a final output.

            Make sure that your the amount of tools you call/use falls within your limit of {tool_call_limit} calls.
        """)
        ],
        db=db,
        add_history_to_context=True,  # allows retrieving session context from db
        num_history_runs=20,
        add_datetime_to_context=True,
        search_session_history=True,
        num_history_sessions=20,
        # DB tools
        read_chat_history=True,
        read_tool_call_history=True,
        max_tool_calls_from_history=tool_call_limit,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        # Options
        retries=4,
        delay_between_retries=3,
        markdown=True,
        telemetry=False,
    )
