from __future__ import annotations

import hashlib
import io
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from .base import AsyncHttpClient

_API_BASE = "https://api.github.com"
_MAX_TARBALL_BYTES = 100 * 1024 * 1024


class GitHubTokenAuth:
    def __init__(self, token: str) -> None:
        self._token = token

    def getAccessToken(self) -> str:
        return self._token

    async def getNewAccessToken(self) -> str:
        raise Exception("GitHub PAT rejected (401): revoked, expired, or missing scope")

    async def handleAccessToken(self, access_token: str) -> None:  # noqa: ARG002
        return None


@dataclass()
class SkillSpec:
    owner: str
    repo: str
    subpath: str | None = None
    ref: str = "HEAD"

    @classmethod
    def parse(cls: Self, raw: str) -> SkillSpec:
        path, sep, ref = raw.strip().rpartition("@")

        if not sep:
            path, ref = raw.strip(), "HEAD"

        owner, _, rest = path.partition("/")
        repo, _, subpath = rest.partition("/")

        if not (owner and repo and ref):
            raise Exception(f"unparseable skill spec: {raw!r}")

        return SkillSpec(
            owner=owner,
            repo=repo,
            subpath=subpath.strip("/") or None,
            ref=ref,
        )


class GitHubSkillsInterface:
    """Resolve, fetch, and install Agent Skills from GitHub repositories.

    Args:
        http: Optional shared client for pooling/testing. When provided it is
            used as-is and never closed here; when omitted, one is constructed
            and disposed with this instance.
        token: PAT used only when constructing an owned client. Ignored if
            ``http`` is supplied, since that client carries its own auth.
    """

    def __init__(
        self,
        *,
        skills_dir: Path | str = Path(".agents"),
        http: AsyncHttpClient | None = None,
        token: str | None = None,
    ) -> None:
        self._http: AsyncHttpClient = http or AsyncHttpClient(
            base_url=_API_BASE, auth=GitHubTokenAuth(token=token) if token else None
        )

        self.skills_dir = skills_dir if isinstance(skills_dir, Path) else Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        async def resolveSha(self: Self, spec: SkillSpec) -> str:
            """Pin a mutable ref to an immutable commit SHA."""
            try:
                response = await self._http.call(
                    f"/repos/{spec.owner}/{spec.repo}/commits/{spec.ref}",
                    headers={"Accept": "application/vnd.github.sha"},
                )
            # except HttpClientError as exc:
            #     raise SkillSourceError(
            except Exception as exc:
                raise Exception(
                    f"ref resolution failed for {spec.owner}/{spec.repo}@{spec.ref}: "
                    # f"{exc.status_code} {(exc.response_body or '')[:200]}"
                ) from exc
            return response.text.strip()

        async def fetchTree(self, spec: SkillSpec, sha: str, dest: Path) -> Path:
            """Extract the repo subtree at `sha` into `dest`; return the skill root."""
            try:
                payload = await self._http.stream(
                    f"/repos/{spec.owner}/{spec.repo}/tarball/{sha}",
                    max_bytes=_MAX_TARBALL_BYTES,
                )
            # except HttpClientError as exc:
            #     raise SkillSourceError(
            except Exception as exc:
                raise Exception(
                    f"ref resolution failed for {spec.owner}/{spec.repo}@{spec.ref}: "
                    # f"{exc.status_code} {(exc.response_body or '')[:200]}"
                ) from exc

            return self._extractSubtree(payload, spec, dest)

        @staticmethod
        def _extractSubtree(payload: bytes, spec: SkillSpec, dest: Path) -> Path:
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
                first = next(iter(tar.getnames()), None)
                if first is None:
                    raise Exception("tarball is empty")

                prefix = first.split("/", 1)[0]  # {owner}-{repo}-{sha7}
                wanted = f"{prefix}/{spec.subpath}/" if spec.subpath else f"{prefix}/"

                members = [m for m in tar.getmembers() if m.name.startswith(wanted)]
                if not members:
                    raise Exception(f"subpath not found in tree: {spec.subpath!r}")

                # filter="data" blocks ../ traversal, symlinks, and device nodes
                tar.extractall(dest, members=members, filter="data")
                print("extracted %d members to %s", len(members), dest)

            return dest / wanted.rstrip("/")

        @staticmethod
        def treeDigest(root: Path) -> str:
            """Stable content hash over the skill tree, for lockfile integrity."""
            digest = hashlib.sha256()
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())

            return digest.hexdigest()
