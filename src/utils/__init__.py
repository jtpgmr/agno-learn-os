from agno.tools.shell import ShellTools
from agno.tools.file import FileTools
from pathlib import Path

from agno.skills import LocalSkills, SkillLoader, Skills
from agno.tools.workspace import Workspace as WorkspaceTools


def getSessionDirectory(workspace_dir: str | Path, session_id) -> Path:
    if isinstance(workspace_dir, str):
        workspace_dir = Path(workspace_dir)

    session_workspace_dir = workspace_dir / "workspaces" / (session_id or "")
    session_workspace_dir.mkdir(parents=True, exist_ok=True)

    return session_workspace_dir


def getSessionFileTools(
    path: str | Path,
    *,
    session_id: str | None = None,
) -> FileTools:
    workspace_dir = getSessionDirectory(path, session_id)

    return FileTools(base_dir=workspace_dir)


def getSessionShellTools(
    path: str | Path,
    *,
    session_id: str | None = None,
) -> ShellTools:
    workspace_dir = getSessionDirectory(path, session_id)

    return ShellTools(base_dir=workspace_dir)


def getSessionWorkspaceTools(
    path: str | Path,
    *,
    session_id: str | None = None,
    allowed_permissions: list[str] | None = None,
) -> WorkspaceTools:
    workspace_dir = getSessionDirectory(path, session_id)

    # allowed_permissions = (
    #     (WorkspaceTools.READ_TOOLS if read_only else WorkspaceTools.ALL_TOOLS)
    #     if not permissions
    #     else list(set(filter(lambda x: x in WorkspaceTools.ALL_TOOLS, permissions)))
    # )

    return WorkspaceTools(root=workspace_dir, allowed=allowed_permissions)


def getAgentSkills(path: str | Path) -> Skills:
    if isinstance(path, str):
        path = Path(path)

    skills_dir: Path = path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    skills_collection: list[SkillLoader] = [LocalSkills(str(skills_dir))]

    return Skills(loaders=skills_collection)
