from typing import TypedDict
from src.core.settings import AppSettings, GoogleDriveSettings
from agno.tools.google_drive import GoogleDriveTools

DRIVE_SCOPES: list[str] = ["https://www.googleapis.com/auth/drive.readonly"]


class _DriveTools(TypedDict):
    list_files: bool
    search_files: bool
    read_file: bool
    upload_file: bool
    download_file: bool
    include_trashed: bool


def configureDriveTools(settings: AppSettings) -> GoogleDriveTools | None:
    drive_settings: GoogleDriveSettings = settings.tools.google_drive

    tools: _DriveTools = {
        "list_files": True,
        "search_files": True,
        "read_file": True,
        # Explicit, though these are already the defaults. This agent reads a
        # resume; it has no reason to put anything back.
        "upload_file": False,
        "download_file": False,
        "include_trashed": False,
        # "max_read_size": drive_settings.max_read_bytes,
    }

    if drive_settings.service_account_path:
        # logger.info("drive auth=service_account path=%s", drive.service_account_path)
        return GoogleDriveTools(
            service_account_path=str(drive_settings.service_account_path),
            scopes=DRIVE_SCOPES,
            # Only valid on Workspace accounts with domain-wide delegation
            # configured. Personal Gmail accounts must share the file instead.
            # delegated_user=drive.delegated_user,
            **tools,
        )

    return None
