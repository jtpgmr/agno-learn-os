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
from agno.tools.reasoning import ReasoningTools
from agno.tools.workspace import Workspace as WorkspaceTools

from src.core import AppSettings, getDatabase, getResponseModel, getSettings
from src.core.utils.agent import excludeTools, getAgentSkills, getSessionWorkspace
from src.tools import DevToTools

# TODO: Tools and features to explore and implement
# from agno.tools.websearch import WebSearchTools
# from agno.tools.youtube import YouTubeTools
# from agno.learn import LearningMachine
# from agno.tools.knowledge import Knowledge as KnowledgeTools
# from agno.knowledge import Knowledge
# from agno.tools.memory import MemoryTools
# from agno.tools.postgres import PostgresTools
# from agno.memory import MemoryManager, UserMemory
# from agno.tools.email import EmailTools


def buildSoftwareNewsFinder(
    settings: AppSettings | None = None,
    session_id: str | None = None,
    *,
    db: AsyncPostgresDb | None = None,
    response_model: Model | None = None,
    read_only=True,
    allow_delete=False,
) -> Agent:
    settings = settings or getSettings()
    skills: Skills | None = None

    # TODO: Implement a better way of administering read/write/delete permissions for each toolkit
    allowed_tools: dict[type[Toolkit], dict[str, Any]] = {}
    tool_call_limit = 30

    # TODO: add a client-side logger for displaying details such as tool configuration
    tools: list[Toolkit] = [
        DuckDuckGoTools(),
        DevToTools(),
        HackerNewsTools(),
        ReasoningTools(
            instructions=dedent("""
                Before finalizing any research brief, reason explicitly:
                1. State what claim each source supports and its tier (docs/repo >
                engineering blog > dev.to > generic web).
                2. Check for conflict between the two search toolkits (Exa vs Tavily).
                If they disagree, note the disagreement and which has stronger evidence.
                3. List what is still missing or stale (>N days).
                4. Only then conclude a ranked, de-duplicated brief.
            """),
            add_instructions=True,
        ),
    ]

    if settings.tools.exa_api_key:
        tools.append(ExaTools(api_key=settings.tools.exa_api_key.get_secret_value(), all=True))

    if settings.tools.github_access_token:
        allowed_tools[GithubTools] = {
            "access_token": settings.tools.github_access_token.get_secret_value()
        }

    if settings.project_path:
        skills = getAgentSkills(settings.project_path)

    if settings.docs_path:
        tools.append(ArxivTools(all=True, download_dir=settings.docs_path))

    if settings.ai.session_data_path:
        workspace: WorkspaceTools = getSessionWorkspace(
            settings.ai.session_data_path,
            session_id,
            read_only=False,  # set `read_only` to False to allow writing to the workspace folder
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
        model=response_model or getResponseModel(),
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
        db=db or getDatabase(db_url=settings.db.dsn, create_schema=True),
        add_history_to_context=True,  # allows retrieving session context from db
        num_history_runs=20,
        add_datetime_to_context=True,
        search_session_history=True,
        num_history_sessions=20,
        # DB tools
        read_chat_history=True,
        read_tool_call_history=True,
        max_tool_calls_from_history=50,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        # Options
        retries=4,
        delay_between_retries=3,
        markdown=True,
        telemetry=False,
    )
