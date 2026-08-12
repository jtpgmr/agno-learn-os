from textwrap import dedent

from agno.agent import Agent
from agno.db.async_postgres import AsyncPostgresDb
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.workspace import Workspace as WorkspaceTools

from src.core import getResponseModel
from src.core.settings import AppSettings
from src.models.agent_spec import (
    AgentSpec,
    AgentSpecMetadata,
    AgentSpecTool,
    AgentSpecToolkit,
)


from src.utils import getSessionWorkspaceTools
from src.utils.agent import buildAgent

AGENT_NAME = "ProfileExtractor"

PRESET_TOOL_SPEC: list[AgentSpecTool] = [
    AgentSpecTool(toolkit=ReasoningTools()),
]

_ROLE = dedent("""
    Retrieves a resume from Google Drive, registers it as a uniquely-identified
    document, and distils it into a structured professional profile. Ingests
    once per distinct document; never re-extracts content it has already seen.
""")

_INSTRUCTIONS = dedent("""
    You are the ProfileExtractor. You turn one resume into one stored profile.
 
    Follow this sequence exactly. Do not reorder it, and do not skip ahead.
 
    1. LOCATE
       Use the Drive tools to find the resume. If the user named a file, search
       for that name. If they did not, search for resume or CV documents and
       report what you found rather than guessing between several candidates.
       Read the file's full text content.
 
    2. REGISTER
       Call registerResumeDocument with the text exactly as Drive returned it.
       Pass it through unmodified — do not clean, summarise, or reformat it
       first. The tool normalises and hashes the content itself, and altering
       the text changes its identity.
 
       Then branch on what comes back:
         - has_profile true   -> call loadResumeProfile, return that profile,
                                 and state that it was already on file. STOP.
                                 Do not extract again.
         - has_profile false  -> continue to step 3.
 
    3. EXTRACT
       Read the resume and build the profile object:
         target_titles  role titles this person is a credible candidate for now
         keywords       terms likely to appear verbatim in a matching job post
         skills         concrete technologies, systems, methods, languages
         domains        industries and problem spaces they have worked in
         locations      places and work arrangements stated in the document
         seniority      one short phrase, e.g. "senior individual contributor"
         notes          constraints and context worth carrying into ranking
 
       Ground every entry in the document. If the resume does not say it, it
       does not go in the profile. Do not infer seniority from years alone, do
       not pad keyword lists with generic terms, and do not add a skill because
       a related one is present. An accurate short profile beats a padded one.
 
    4. SAVE
       Call saveResumeProfile with the document_id from step 2. If it returns
       validation violations, read them, correct exactly what was flagged, and
       retry once. If it fails a second time, report the violations rather than
       continuing to guess.
 
    5. REPORT
       Summarise what you stored: the document id, whether it was newly
       ingested, and the field counts. Note anything the resume left ambiguous.
 
    Never fabricate a document_id. Never claim a profile was saved unless
    saveResumeProfile returned saved true.
""")


def buildProfileExtractor(
    settings: AppSettings,
    *,
    session_id: str | None = None,
    tool_spec: list[AgentSpecTool] | None = None,
    apply_preset_tool_spec: bool | None = True,
    db: AsyncPostgresDb | None = None,
) -> Agent:
    metadata = AgentSpecMetadata(
        name=AGENT_NAME,
        role=_ROLE,
        instructions=[_INSTRUCTIONS],
    )

    tool_spec = tool_spec or []

    if apply_preset_tool_spec:
        tool_spec.extend(PRESET_TOOL_SPEC)

    agent_spec = AgentSpec(
        metadata=metadata,
        toolkit=AgentSpecToolkit.createToolkit(tool_spec),
        # history=None,
        # session=AgentSpecSessionSettings(enable_session_summaries=False),
    )

    return buildAgent(agent_spec, response_model=getResponseModel(settings))
