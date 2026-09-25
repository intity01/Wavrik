"""One independent cancellable download job."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QRunnable, pyqtSlot

from src.domain.models import (
    DownloadJobConfig,
    DownloadResult,
    HistoryRecord,
    JobState,
)
from src.domain.utils import friendly_error


class DownloadWorker(QRunnable):
    def __init__(
        self, config_or_url: DownloadJobConfig | str, *args: Any, **kwargs: Any,
    ) -> None:
        super().__init__()
        cfg = (
            config_or_url
            if isinstance(config_or_url, DownloadJobConfig)
            else self._unpack_legacy_config(config_or_url, args, kwargs)
        )
        self.url, self.preset = cfg.url, cfg.preset
        dl = cfg.downloader
        self.downloader = dl.newSession() if hasattr(dl, "newSession") else dl
        self.output_dir, self.signals = Path(cfg.output_dir), cfg.signals
        self.history, self.title, self.engine = cfg.history, cfg.title, cfg.engine
        self.cancelled = False
        self._last_status: tuple[str, str] | None = None
        self._last_progress_time: float = 0.0
        self.setAutoDelete(True)

    def _unpack_legacy_config(
        self, url: str, args: tuple[Any, ...], kwargs: dict[str, Any],
    ) -> DownloadJobConfig:
        k = kwargs.get
        return DownloadJobConfig(
            url=url,
            downloader=args[0] if len(args) > 0 else kwargs["downloader"],
            preset=args[1] if len(args) > 1 else kwargs["preset"],
            output_dir=Path(args[2] if len(args) > 2 else kwargs["output_dir"]),
            signals=args[3] if len(args) > 3 else kwargs["signals"],
            history=args[4] if len(args) > 4 else k("history"),
            title=args[5] if len(args) > 5 else k("title", ""),
            engine=args[6] if len(args) > 6 else k("engine", "auto"),
        )

    def cancel(self) -> None:
        self.cancelled = True
        self.downloader.cancelDownload()

    def _emit_status(self, state: str, label: str) -> None:
        if self._last_status != (state, label):
            self._last_status = (state, label)
            self.signals.status.emit(self.url, state, label)

    def _progress(self, info: dict) -> None:
        state = info.get("status", "downloading")
        label = "Processing file" if state == "processing" else "Downloading"
        self._emit_status(state, label)
        percent = float(info.get("percent", 0))
        now = time.monotonic()
        if (
            self._last_progress_time == 0.0
            or percent >= 100.0
            or (now - self._last_progress_time) >= 0.1
        ):
            self._last_progress_time = now
            self.signals.progress.emit(
                self.url, percent,
                str(info.get("speed", "—")), str(info.get("eta", "—")),
            )

    @pyqtSlot()
    def run(self) -> None:
        if self.cancelled:
            result = DownloadResult(False, JobState.CANCELLED)
            self._record(result)
            self.signals.finished.emit(self.url, result)
            return
        label = {"auto": "Auto route", "native": "Native engine", "yt-dlp": "yt-dlp engine"}.get(self.engine, "Auto route")
        self._emit_status("downloading", f"Starting with {label}")
        try:
            result = self.downloader.download(
                self.url, self.output_dir, self.preset, self._progress, self.engine
            )
            self._record(result)
            # Emit error before finished for failed states to preserve error message
            if result.state == JobState.FAILED and result.error:
                self.signals.error.emit(self.url, result.error)
            self.signals.finished.emit(self.url, result)
        except Exception as exc:  # noqa: BLE001 - worker boundary must protect the Qt thread.
            error_result = DownloadResult(False, JobState.FAILED, error=friendly_error(str(exc)), engine=self.engine)
            try:
                self._record(error_result)
            except Exception:  # noqa: BLE001 - history failure must not stop the worker signal.
                self.signals.error.emit(self.url, "Could not record download history.")
            self.signals.error.emit(self.url, error_result.error)
            self.signals.finished.emit(self.url, error_result)

    def _record(self, result) -> None:
        try:
            file_path = result.file_path
            size = file_path.stat().st_size if file_path and file_path.exists() else 0
            thumbnail_path = str(result.thumbnail_path) if result.thumbnail_path else ""
            additional_info = f" (+{len(result.additional_files)} more files)" if result.additional_files else ""
            rec = HistoryRecord(
                url=self.url,
                title=self.title,
                media_type=self.preset.media_type,
                format=f"{self.preset.label} · {result.engine}{additional_info}",
                file_path=str(file_path or ""),
                is_success=result.success,
                file_size=size,
                status=result.state.value.lower(),
                error=result.error,
                thumbnail_path=thumbnail_path,
            )
            self.history.addEntry(rec)
            if result.state == JobState.CANCELLED:
                self._emit_status("cancelled", "Download cancelled")
            elif result.state == JobState.COMPLETED:
                message = f"Saved with {result.engine}"
                if result.additional_files:
                    message += f" ({len(result.additional_files) + 1} files)"
                self._emit_status("completed", message)
        except Exception:  # noqa: BLE001 - history failure must not stop the worker signal.
            self.signals.error.emit(self.url, "Could not record download history.")
