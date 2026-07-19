from __future__ import annotations

from dataclasses import dataclass, field

from agno.skills import Skills
from agno.tools import Function, Toolkit


@dataclass(slots=True)
class AgentSpecMetadata:
    name: str
    role: str
    id: str | None = None
    instructions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.id is None:
            self.id = self.name.lower().replace(" ", "-")


@dataclass(slots=True)
class AgentSpecTool:
    toolkit: Toolkit
    read_only: bool = True
    allow_delete: bool = False
    permissions: set[str] | None = None

    def applyAllowedTools(self) -> AgentSpecTool:
        from src.models.constants import DELETE_KEYWORDS, WRITE_KEYWORDS

        exclude_keywords: tuple = ()
        toolkit = self.toolkit

        if self.read_only:
            exclude_keywords = WRITE_KEYWORDS + DELETE_KEYWORDS

        if not self.read_only and not self.allow_delete:
            exclude_keywords = DELETE_KEYWORDS

        for registry in (toolkit.functions, toolkit.async_functions):
            for name in [n for n in registry if any(w in n.lower() for w in exclude_keywords)]:
                del registry[name]

        self.toolkit = toolkit
        return self

    def renameTools(self) -> AgentSpecTool:
        """Rename a toolkit's tools before the agent registers them, e.g. to avoid name
        collisions between toolkits ({"think": "reasoning_think"}). `prefix` renames every
        tool not already covered by `names` to "<prefix>_<name>".
        """
        toolkit = self.toolkit

        for attr in ("functions", "async_functions"):
            registry: dict[str, Function] = getattr(toolkit, attr)
            renamed: dict[str, Function] = {}
            toolkit_prefix = (
                toolkit.name.lower().split("_tools")[0] or toolkit.name.lower().split("_")[0]
            )

            for name, function in registry.items():
                combined_name = f"{toolkit_prefix}_{name}"

                parts = combined_name.split("_")
                new_function_name = "_".join(dict.fromkeys(parts))

                function.name = new_function_name
                renamed[new_function_name] = function

            setattr(toolkit, attr, renamed)

        self.toolkit = toolkit
        return self


@dataclass(frozen=True, slots=True)
class AgentSpecToolkitSettings:
    tool_call_limit: int = 0


@dataclass(frozen=True, slots=True)
class AgentSpecToolkit:
    tools: list[Toolkit] = field(default_factory=list)
    settings: AgentSpecToolkitSettings = field(default=AgentSpecToolkitSettings())

    def createToolkit(agent_spec: list[AgentSpecTool]) -> AgentSpecToolkit:  # noqa N805
        tools = []
        tool_call_limit = 0
        for tool in agent_spec:
            tools.append(tool.applyAllowedTools().renameTools().toolkit)
            tool_call_limit += 5

        return AgentSpecToolkit(
            tools=tools, settings=AgentSpecToolkitSettings(tool_call_limit=tool_call_limit)
        )


@dataclass(frozen=True, slots=True)
class AgentSpecHistorySettings:
    read_chat_history: bool = True
    read_tool_call_history: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = 20
    search_session_history: bool = True
    num_history_sessions: int = 20


@dataclass(frozen=True, slots=True)
class AgentSpecSessionSettings:
    enable_session_summaries: bool = True
    add_session_summary_to_context: bool = True
    add_datetime_to_context: bool = True


@dataclass(frozen=True, slots=True)
class AgentSpecOptions:
    retries: int = 4
    delay_between_retries: int = 3
    markdown: bool = True
    telemetry: bool = False


@dataclass(frozen=True, slots=True)
class AgentSpec:
    metadata: AgentSpecMetadata
    # model: Model
    use_db: bool = False
    toolkit: AgentSpecToolkit = field(default=AgentSpecToolkit())
    skills: Skills | None = None
    history: AgentSpecHistorySettings | None = field(default=AgentSpecHistorySettings())
    session: AgentSpecSessionSettings | None = field(default=AgentSpecSessionSettings())
    options: AgentSpecOptions | None = field(default=AgentSpecOptions())
