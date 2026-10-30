import hashlib
from pathlib import Path

import pytest

from src.core.updater import API_VERSION, UpdateError, UpdateManager


class FakeResponse:
    def __init__(self, *, data=None, content=b"", url="https://api.github.com/", status_code=200):
        self._data = data
        self._content = content
        self.url = url
        self.status_code = status_code
        self.headers = {"content-length": str(len(content))}

    def raise_for_status(self):
        return None

    def json(self):
        return self._data

    def iter_content(self, _size):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _release(content: bytes, *, version="2.1.0", immutable=True):
    digest = hashlib.sha256(content).hexdigest()
    return {
        "tag_name": f"v{version}",
        "body": "Maintenance release.",
        "html_url": "https://github.com/owner/repo/releases/tag/v2.1.0",
        "immutable": immutable,
        "assets": [
            {
                "name": "MediaDownloaderPRO-Setup.exe",
                "browser_download_url": "https://github.com/owner/repo/releases/download/v2.1.0/app.exe",
                "size": len(content),
                "digest": f"sha256:{digest}",
                "state": "uploaded",
            }
        ],
    }


def test_update_check_parses_verified_release_and_api_headers():
    session = FakeSession(FakeResponse(data=_release(b"package")))
    manager = UpdateManager("2.0.0", "owner/repo", session=session)
    info = manager.checkForUpdates()
    assert info and info.version == "2.1.0"
    assert info.can_download_safely
    assert info.asset and info.asset.name.endswith(".exe")
    assert session.calls[0][1]["headers"]["X-GitHub-Api-Version"] == API_VERSION


def test_repository_without_releases_reports_no_update():
    session = FakeSession(FakeResponse(data={"message": "Not Found"}, status_code=404))
    manager = UpdateManager("2.1.0", "owner/repo", session=session)
    assert manager.checkForUpdates() is None


def test_equal_version_with_shorter_semver_is_not_an_update():
    session = FakeSession(FakeResponse(data=_release(b"package", version="2.1")))
    manager = UpdateManager("2.1.0", "owner/repo", session=session)
    assert manager.checkForUpdates() is None


def test_verified_download_checks_sha256_and_uses_atomic_target(tmp_path: Path):
    content = b"trusted package"
    session = FakeSession(
        FakeResponse(data=_release(content)),
        FakeResponse(content=content, url="https://release-assets.githubusercontent.com/package"),
    )
    manager = UpdateManager("2.0.0", "owner/repo", session=session)
    info = manager.checkForUpdates()
    target = manager.downloadVerified(info, tmp_path)
    assert target.read_bytes() == content
    assert not target.with_suffix(target.suffix + ".part").exists()


def test_unverified_release_cannot_be_downloaded_in_app(tmp_path: Path):
    session = FakeSession(FakeResponse(data=_release(b"package", immutable=False)))
    manager = UpdateManager("2.0.0", "owner/repo", session=session)
    info = manager.checkForUpdates()
    assert info and not info.can_download_safely
    with pytest.raises(UpdateError):
        manager.downloadVerified(info, tmp_path)


def test_unconfigured_update_manager_does_not_make_a_network_request():
    session = FakeSession()
    manager = UpdateManager("2.0.0", "", session=session)
    with pytest.raises(UpdateError, match="not configured"):
        manager.checkForUpdates()
    assert not session.calls
