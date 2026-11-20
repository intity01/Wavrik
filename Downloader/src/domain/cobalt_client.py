"""HTTP client for Cobalt media extraction API."""

from __future__ import annotations

import requests

from src.core.config import Config
from .cobalt_models import CobaltRequest, CobaltResponse
from .cobalt_security import validate_instance_url
from .models import DownloadPreset, MediaType


class CobaltError(RuntimeError):
    """Actionable Cobalt API or connection error."""


def _map_audio_format(container: str) -> str:
    fmt = container.lower()
    if fmt in {"mp3", "wav", "opus"}:
        return fmt
    if fmt in {"ogg", "vorbis"}:
        return "ogg"
    if fmt == "best":
        return "best"
    return "mp3"


def _map_audio_bitrate(bitrate: str | None) -> str:
    if bitrate in {"320", "256", "128", "96", "64"}:
        return bitrate
    if bitrate == "0":
        return "320"
    return "128"


def preset_to_cobalt_request(url: str, preset: DownloadPreset) -> CobaltRequest:
    """Map a Wavrik DownloadPreset to a Cobalt API request payload."""
    is_audio = preset.media_type == MediaType.AUDIO
    download_mode = "audio" if is_audio else "auto"
    audio_fmt = _map_audio_format(preset.container)
    audio_br = _map_audio_bitrate(preset.audio_bitrate)
    video_q = str(preset.video_height) if preset.video_height else "1080"
    return CobaltRequest(
        url=url,
        videoQuality=video_q,
        audioFormat=audio_fmt,
        audioBitrate=audio_br,
        downloadMode=download_mode,
    )


class CobaltClient:
    """HTTP client interacting with Cobalt v10 API instances."""

    def __init__(
        self,
        base_url: str = "https://api.cobalt.tools/",
        api_key: str = "",
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/") + "/"
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.is_valid = bool(validate_instance_url(self.base_url))

    def _require_valid_instance(self) -> None:
        if not self.is_valid:
            raise CobaltError("Cobalt instance URL must use https (http is only allowed for localhost).")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"WavrikMediaEngine/{Config.VERSION}",
        }
        if self.api_key and self.is_valid:
            headers["Authorization"] = f"Api-Key {self.api_key}"
        return headers

    def is_alive(self) -> bool:
        """Probe GET / endpoint for instance reachability."""
        if not self.is_valid:
            return False
        try:
            resp = requests.get(
                self.base_url,
                headers={"Accept": "application/json", "User-Agent": f"WavrikMediaEngine/{Config.VERSION}"},
                timeout=3.0,
            )
            return resp.status_code < 400
        except (requests.RequestException, OSError):
            return False

    def resolve_stream(self, req: CobaltRequest) -> CobaltResponse:
        """Resolve media stream information via Cobalt POST /."""
        self._require_valid_instance()
        try:
            resp = requests.post(
                self.base_url,
                json=req.to_dict(),
                headers=self._headers(),
                timeout=self.timeout,
                allow_redirects=False,
            )
            self._handle_status(resp)
            return CobaltResponse.from_dict(resp.json())
        except requests.Timeout as exc:
            raise CobaltError("Cobalt request timed out.") from exc
        except requests.RequestException as exc:
            raise CobaltError(f"Cobalt network error: {exc}") from exc
        except ValueError as exc:
            raise CobaltError("Cobalt returned an invalid JSON response.") from exc

    def _handle_status(self, resp: requests.Response) -> None:
        if resp.status_code == 400:
            err = self._extract_error(resp) or "Invalid URL or unsupported media."
            raise CobaltError(f"Cobalt API rejected request: {err}")
        if resp.status_code == 401:
            raise CobaltError("Cobalt API authorization failed. Check your API key.")
        if resp.status_code == 429:
            raise CobaltError("Cobalt rate limit reached. Please wait before retrying.")
        if resp.status_code >= 300:
            raise CobaltError(f"Cobalt service returned HTTP {resp.status_code}.")

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            data = resp.json()
            if isinstance(data, dict):
                err = data.get("error")
                if isinstance(err, dict) and err.get("code"):
                    return str(err["code"])
                if isinstance(err, str):
                    return err
                if data.get("text"):
                    return str(data["text"])
        except Exception:
            pass
        return ""
