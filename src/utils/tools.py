from agno.tools import Function, Toolkit

from src.models.constants import DELETE_KEYWORDS, WRITE_KEYWORDS
from src.models.agent_spec import AgentSpecTool


def excludeTools(
    tool_kit: Toolkit, *, read_only: bool | None = True, allow_delete: bool | None = False
) -> Toolkit:
    exclude_keywords: tuple = ()

    if read_only:
        exclude_keywords = WRITE_KEYWORDS + DELETE_KEYWORDS

    if not read_only and not allow_delete:
        exclude_keywords = DELETE_KEYWORDS

    # for name in [n for n in tool_kit.functions if any(w in n.lower() for w in exclude_keywords)]:
    #     del tool_kit.functions[name]

    for registry in (tool_kit.functions, tool_kit.async_functions):
        for name in [n for n in registry if any(w in n.lower() for w in exclude_keywords)]:
            del registry[name]

    return tool_kit
