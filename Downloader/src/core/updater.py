"""GitHub release checks and verified package downloads."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import requests

from .update_models import ReleaseAsset, UpdateInfo

API_VERSION = "2026-03-10"
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ALLOWED_HOSTS = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}


class UpdateError(RuntimeError):
    """Safe, user-facing update error."""


class UpdateManager:
    def __init__(self, currentVersion: str, repoUrl: str, logger=None, session=None):
        self.currentVersion = currentVersion
        self.repoUrl = repoUrl
        self.logger = logger
        self._session = session or requests.Session()
        self.updateUrl = f"https://api.github.com/repos/{repoUrl}/releases/latest"

    @property
    def isConfigured(self) -> bool:
        return bool(_REPO.fullmatch(self.repoUrl))

    def getCurrentVersion(self) -> str:
        return self.currentVersion

    def checkForUpdates(self) -> UpdateInfo | None:
        if not self.isConfigured:
            raise UpdateError("Updates are not configured for this build.")
        data = self._latest_release()
        version = str(data.get("tag_name", "")).lstrip("vV")
        if not version or not self._isNewer(version):
            return None
        return UpdateInfo(
            version=version,
            notes=str(data.get("body", "")).strip(),
            release_url=str(data.get("html_url", "")),
            immutable=bool(data.get("immutable", False)),
            asset=self._select_asset(data.get("assets", [])),
        )

    def downloadVerified(
        self,
        info: UpdateInfo,
        outputDir: Path,
        progress: Callable[[int], None] | None = None,
    ) -> Path:
        if not info.can_download_safely or not info.asset:
            raise UpdateError("This release is not available as a verified in-app download.")
        outputDir.mkdir(parents=True, exist_ok=True)
        target = outputDir / Path(info.asset.name).name
        temporary = target.with_suffix(target.suffix + ".part")
        digest = hashlib.sha256()
        try:
            self._stream_asset(info.asset, temporary, digest, progress)
            if digest.hexdigest().lower() != info.asset.sha256.lower():
                raise UpdateError("The downloaded package failed its SHA-256 integrity check.")
            os.replace(temporary, target)
            return target
        finally:
            temporary.unlink(missing_ok=True)

    def _latest_release(self) -> dict:
        try:
            response = self._session.get(
                self.updateUrl,
                headers=self._headers(),
                timeout=(5, 15),
            )
            if response.status_code != 404:  # 404 = the repository has no published release yet
                response.raise_for_status()
            data = response.json() if response.status_code != 404 else {}
        except (requests.RequestException, ValueError) as exc:
            self._log_warning(exc)
            raise UpdateError("Could not check GitHub for updates. Check your connection and try again.") from exc
        return data if isinstance(data, dict) else {}

    def _stream_asset(self, asset, path: Path, digest, progress) -> None:
        try:
            with self._session.get(asset.url, stream=True, timeout=(5, 60), allow_redirects=True) as response:
                response.raise_for_status()
                if urlparse(response.url).hostname not in _ALLOWED_HOSTS:
                    raise UpdateError("GitHub redirected the download to an unexpected host.")
                total = min(int(response.headers.get("content-length", asset.size or 0)), 600_000_000)
                written = 0
                with path.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 256):
                        if not chunk:
                            continue
                        written += len(chunk)
                        if written > 600_000_000:
                            raise UpdateError("The update package is larger than the safety limit.")
                        handle.write(chunk)
                        digest.update(chunk)
                        if progress and total:
                            progress(min(100, int(written * 100 / total)))
        except requests.RequestException as exc:
            raise UpdateError("The update package could not be downloaded from GitHub.") from exc

    def _select_asset(self, assets) -> ReleaseAsset | None:
        candidates = [item for item in assets if isinstance(item, dict) and item.get("state") == "uploaded"]
        candidates.sort(key=lambda item: self._asset_score(str(item.get("name", ""))), reverse=True)
        for item in candidates:
            digest = str(item.get("digest", ""))
            url = str(item.get("browser_download_url", ""))
            if digest.startswith("sha256:") and urlparse(url).hostname == "github.com":
                return ReleaseAsset(str(item.get("name", "update")), url, int(item.get("size", 0)), digest[7:])
        return None

    @staticmethod
    def _asset_score(name: str) -> int:
        lower = name.lower()
        score = 0
        score += 8 if lower.endswith((".exe", ".msi")) else 3 if lower.endswith(".zip") else -20
        score += 5 if any(term in lower for term in ("setup", "installer")) else 0
        score += 4 if any(term in lower for term in ("windows", "win64", "x64")) else 0
        return score

    def _isNewer(self, latest: str) -> bool:
        return _version_tuple(latest) > _version_tuple(self.currentVersion)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": f"MediaDownloaderPRO/{self.currentVersion}",
        }

    def _log_warning(self, exc: Exception) -> None:
        if self.logger:
            self.logger.warning(f"Update check failed: {exc}")


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = [int(item) for item in re.findall(r"\d+", value.split("-", 1)[0])]
    return tuple((numbers + [0, 0, 0, 0])[:4])
