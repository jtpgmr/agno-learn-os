from pathlib import Path
from uuid import uuid4

from agno.skills import LocalSkills, SkillLoader, Skills
from agno.tools import Toolkit
from agno.tools.workspace import Workspace as WorkspaceTools

READ_KEYWORDS = ("read", "get", "list", "search")
WRITE_KEYWORDS = ("create", "edit", "write", "add", "insert", "upsert", "shell")
DELETE_KEYWORDS = ("delete", "remove", "drop", "destroy")


def getSessionWorkspace(
    path: str | Path,
    session_id: str | None = None,
    *,
    permissions: list[str] | None = None,
    read_only: bool | None = True,
) -> WorkspaceTools:
    if isinstance(path, str):
        path = Path(path)

    workspace_dir = path / "workspaces" / (session_id or str(uuid4()))
    workspace_dir.mkdir(parents=True, exist_ok=True)

    allowed_permissions = (
        (WorkspaceTools.READ_TOOLS if read_only else WorkspaceTools.ALL_TOOLS)
        if not permissions
        else list(set(filter(lambda x: x in WorkspaceTools.ALL_TOOLS, permissions)))
    )

    return WorkspaceTools(root=workspace_dir, allowed=allowed_permissions)


def getAgentSkills(path: str | Path) -> Skills:
    if isinstance(path, str):
        path = Path(path)

    skills_dir: Path = path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    skills_collection: list[SkillLoader] = [LocalSkills(str(skills_dir))]

    return Skills(loaders=skills_collection)


def excludeTools(
    tool_kit: Toolkit, *, read_only: bool | None = True, allow_delete: bool | None = False
) -> Toolkit:
    exclude_keywords: tuple = ()

    if read_only:
        exclude_keywords = WRITE_KEYWORDS + DELETE_KEYWORDS

    if not read_only and not allow_delete:
        exclude_keywords = DELETE_KEYWORDS

    for name in [n for n in tool_kit.functions if any(w in n.lower() for w in exclude_keywords)]:
        del tool_kit.functions[name]

    return tool_kit
