from textwrap import dedent

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.tools.github import GithubTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.reasoning import ReasoningTools

from src.core import getResponseModel
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)
from src.tools import DevToTools
from src.utils.agent import buildAgent

AGENT_NAME = "Tech Scout"
STALE_AFTER_DAYS = 120


def buildTechScout(settings: AppSettings) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=dedent("""
            Discovers candidate articles/repos/papers across the web, GitHub, dev.to, HN and arXiv.
            Returns raw candidates with metadata; does NOT rank or write files.
        """),
        instructions=[
            dedent("""
            You are a feature tester agent for this Agno framework, whose purpose is to keep me up-to-date with the latest in tech, including
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
    )

    tools_spec: list[AgentSpecTool] = [
        AgentSpecTool(toolkit=DuckDuckGoTools()),
        AgentSpecTool(toolkit=DevToTools()),
        AgentSpecTool(toolkit=HackerNewsTools()),
        AgentSpecTool(
            toolkit=ReasoningTools(
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
                    {STALE_AFTER_DAYS} days as potentially stale, and note where you lack a recent source.

                    4. Name the gaps. List what the brief still cannot answer from the gathered sources.

                    5. Only then write the brief: ranked by evidence strength, de-duplicated by canonical
                    URL, each item citing its source and tier. Prefer "I could not confirm X" over
                    presenting a weak claim as settled.
            """),
                add_instructions=True,
            )
        ),
    ]

    if settings.tools.github_access_token and (
        gh_token := settings.tools.github_access_token.get_secret_value()
    ):
        tools_spec.append(AgentSpecTool(toolkit=GithubTools(access_token=gh_token)))

    if settings.tools.exa_api_key and (exa_token := settings.tools.exa_api_key.get_secret_value()):
        tools_spec.append(AgentSpecTool(toolkit=ExaTools(api_key=exa_token)))

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tools_spec),
        history=None,
    )

    return buildAgent(agent_spec, response_model=getResponseModel(settings))
