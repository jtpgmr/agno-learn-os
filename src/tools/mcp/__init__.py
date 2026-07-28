from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from agno.tools.mcp import StreamableHTTPClientParams
from mcp import StdioServerParameters

from src.core.settings import AppSettings

AVAILABLE_STDIO_COMMANDS: list[Literal["uvx"]] = ["uvx"]
HTTP_MCP: tuple[str, ...] = ("gitmcp.io/docs", "mcp.deepwiki.com/mcp", "docs.agno.com/mcp")
# HTTP_MCP: set[str] = {"gitmcp.io/docs", "mcp.deepwiki.com/mcp"}


@dataclass
class StdioMcpSetupOptions:
    mcp: str
    args: list[str] = field(default_factory=list[str])
    env: dict[str, str] | None = None


def getPresetStdioMcpServers(settings: AppSettings) -> list[StdioServerParameters]:
    _STDIO_MCP_SERVERS: dict[str, list[StdioMcpSetupOptions]] = {  # noqa N806
        "uvx": [
            StdioMcpSetupOptions(
                mcp="mcp-server-docker",
                env={"DOCKER_HOST": docker_host} if (docker_host := settings.docker_host) else None,
            ),
            # StdioMcpSetupOptions(mcp="docker-mcp"),
            StdioMcpSetupOptions(mcp="markitdown-mcp"),
            # StdioMcpSetupOptions(mcp="mcp-pandoc", args=["--with", "pypandoc-binary"]),
        ]
    }

    server_params_list: list[StdioServerParameters] = []

    for command in AVAILABLE_STDIO_COMMANDS:
        mcp_options = _STDIO_MCP_SERVERS.get(command)

        if mcp_options:
            for options in mcp_options:
                print(options)
                server_params_list.append(
                    StdioServerParameters(
                        command=command,
                        args=[
                            *(options.args or []),
                            options.mcp,
                        ],  # unpack each string in the list with *
                        env=options.env,
                    )
                )

    return server_params_list


@lru_cache
def getPresetMcpServerUrls() -> list[StreamableHTTPClientParams]:
    server_params_list: list[StreamableHTTPClientParams] = []

    for url in HTTP_MCP:
        parsed = urlparse(url)
        if not parsed.scheme:
            parsed = urlparse(f"https://{url}")

        if not parsed.netloc:
            print(f"Invalid MCP server URL: {url!r}")
            continue

        server_params_list.append(StreamableHTTPClientParams(parsed.geturl()))

    return server_params_list
