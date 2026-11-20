"""User-controlled turbo download settings carried alongside a request callable."""

from __future__ import annotations

from dataclasses import dataclass

MIN_THREADS = 1
MAX_THREADS = 8
DEFAULT_THREADS = 4


def _clamp_threads(value) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return DEFAULT_THREADS
    return max(MIN_THREADS, min(MAX_THREADS, count))


@dataclass(frozen=True)
class TurboSettings:
    """Turbo on/off switch and parallel segment count (1-8)."""

    enabled: bool = True
    threads: int = DEFAULT_THREADS

    @classmethod
    def from_config(cls, config) -> TurboSettings:
        if config is None:
            return cls()
        enabled = config.get("turboDownloadEnabled", True)
        threads = config.get("turboThreadCount", DEFAULT_THREADS)
        return cls(enabled=enabled if isinstance(enabled, bool) else True, threads=_clamp_threads(threads))


class TurboRequests:
    """Wrap a `requests.get`-style callable and attach turbo settings to it."""

    def __init__(self, request_get, settings: TurboSettings) -> None:
        self._request_get = request_get
        self.turbo = TurboSettings(settings.enabled, _clamp_threads(settings.threads))

    def __call__(self, *args, **kwargs):
        return self._request_get(*args, **kwargs)


def settings_of(request_get) -> TurboSettings:
    """Return turbo settings attached to `request_get`, or the defaults."""
    found = getattr(request_get, "turbo", None)
    return found if isinstance(found, TurboSettings) else TurboSettings()
