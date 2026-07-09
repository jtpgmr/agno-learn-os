import asyncio
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

from agno.agent import Agent
from agno.skills import LocalSkills, SkillLoader, Skills
from agno.tools import Toolkit
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.tools.github import GithubTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.workspace import Workspace

# TODO: Tools and features to explore and implement
# from agno.tools.youtube import YouTubeTools
# from agno.tools.arxiv import ArxivTools
# from agno.learn import LearningMachine
# from agno.tools.knowledge import Knowledge as KnowledgeTools
# from agno.knowledge import Knowledge
# from agno.tools.memory import MemoryTools
# from agno.tools.postgres import PostgresTools
# from agno.memory import MemoryManager, UserMemory
from src.core import AppSettings, chatWithAgent, getDatabase, getResponseModel, getSettings
from src.tools import DevToTools


def getSessionWorkspace(
    path: str | Path, session_id: str | None = None, permissions: list[str] | None = None
) -> Workspace:
    if isinstance(path, str):
        path = Path(path)

    workspace_dir = path / "workspaces" / (session_id or str(uuid4()))
    workspace_dir.mkdir(parents=True, exist_ok=True)

    allowed_permissions = (
        Workspace.ALL_TOOLS
        if not permissions
        else list(set(filter(lambda x: x in Workspace.ALL_TOOLS, permissions)))
    )

    return Workspace(root=workspace_dir, allowed=allowed_permissions)


def getAgentSkills(path: str | Path) -> Skills:
    if isinstance(path, str):
        path = Path(path)

    skills_dir: Path = path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    skills_collection: list[SkillLoader] = [LocalSkills(str(skills_dir))]

    return Skills(skills_collection)


def buildSoftwareNewsFinder(settings: AppSettings, session_id: str | None = None) -> Agent:
    skills: Skills | None = None

    # TODO: add a client-side logger for displaying details such as tool configuration
    tools: list[Toolkit] = [DuckDuckGoTools(fixed_max_results=5), DevToTools(), HackerNewsTools()]

    reasoning_tools = ReasoningTools(
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
    )

    tools.append(reasoning_tools)

    # Optionally pair with ThinkingTools for hard decomposition (e.g. planning the
    # research, not just analyzing results):
    # think = ThinkingTools(add_instructions=True)

    if settings.tools.github_access_token:
        tools.append(
            GithubTools(access_token=settings.tools.github_access_token.get_secret_value())
        )

    if settings.tools.exa_api_key:
        tools.append(ExaTools(api_key=settings.tools.exa_api_key.get_secret_value()))

    if settings.ai.context_path:
        tools.append(getSessionWorkspace(settings.ai.context_path, session_id))

        skills = getAgentSkills(settings.ai.context_path)

    return Agent(
        name="Tech News Finder",
        id="tech-news-finder",
        role=("Finds written tutorials and articles on Github and dev.to and engineering blogs."),
        model=getResponseModel(),
        tools=tools,
        tool_call_limit=30,
        skills=skills,
        instructions=[
            # Use GitHub tools only when a valid token is configured.
            dedent("""
            You are a tech news finder/researcher, whose purpose is to keep me up-to-date with the latest in tech, including
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
            """)
        ],
        db=getDatabase(db_url=settings.db.dsn, create_schema=True),
        add_history_to_context=True,  # allows retrieving session context from db
        num_history_runs=3,
        add_datetime_to_context=True,
        search_session_history=True,
        num_history_sessions=2,
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


if __name__ == "__main__":
    settings = getSettings()
    db = getDatabase(db_url=settings.db.dsn, create_schema=True)

    session_id = str(uuid4())
    print("The current session id is:\t", session_id)

    agent = buildSoftwareNewsFinder(settings, session_id)
    asyncio.run(chatWithAgent(agent, session_id=session_id))
