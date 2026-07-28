from pathlib import Path

from agno.skills import LocalSkills, SkillLoader, Skills
from agno.tools.workspace import Workspace as WorkspaceTools


def getSessionWorkspace(
    path: str | Path,
    *,
    session_id: str | None = None,
    # permissions: list[str] | None = None,
    # read_only: bool | None = True,
) -> WorkspaceTools:
    if isinstance(path, str):
        path = Path(path)

    workspace_dir = path / "workspaces" / (session_id or "")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # allowed_permissions = (
    #     (WorkspaceTools.READ_TOOLS if read_only else WorkspaceTools.ALL_TOOLS)
    #     if not permissions
    #     else list(set(filter(lambda x: x in WorkspaceTools.ALL_TOOLS, permissions)))
    # )

    return WorkspaceTools(
        root=workspace_dir,
        #   allowed=allowed_permissions
    )


def getAgentSkills(path: str | Path) -> Skills:
    if isinstance(path, str):
        path = Path(path)

    skills_dir: Path = path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    skills_collection: list[SkillLoader] = [LocalSkills(str(skills_dir))]

    return Skills(loaders=skills_collection)
