"""Playback, preview and export actions of the Audio Tools page."""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.services.audio_pitch import unique_export_path

from .audio_tools_presenter import (
    build_export_name, compute_tempo_ratio, handle_pitch_rendered, open_export_folder,
    set_controls_enabled, start_pitch_render, update_preview_labels,
)


class PlaybackActionsMixin:
    """Expects the host page to provide ``transport``, ``statusLabel`` and the export widgets."""

    def _on_seek_requested(self, sec: float) -> None:
        self.statusLabel.setText(f"Playhead set to {int(sec // 60)}:{int(sec % 60):02d} (25s preview slice)")
        if self.transport.isPlaying():
            self.transport.playSlot(self.transport.activeSlot(), sec)
        else:
            self.transport.seek(sec)

    def _play_original(self) -> None:
        if self._source and self._source.is_file():
            self.transport.playSlot("A", self.waveformWidget.seekPosition())
            self.statusLabel.setText(f"Playing Original (A): {self._source.name}")

    def _stop_playback(self) -> None:
        self.transport.stop()
        self.statusLabel.setText(self._text("at.playback_stopped"))

    def _preview_shifted(self) -> None:
        if self._source and not self._busy:
            folder = Path(tempfile.gettempdir()) / "WavrikPreview"
            folder.mkdir(parents=True, exist_ok=True)
            self._start_render(unique_export_path(folder, self._export_name("wav")), "wav", True)

    def _export_shifted(self) -> None:
        if self._source and not self._busy:
            fmt = str(self.formatCombo.currentData() or "wav")
            self._start_render(unique_export_path(self._cfg.getDownloadPath("audio"), self._export_name(fmt)), fmt, False)

    # Thin delegates kept as methods because Qt signal wiring and tests address them on the page.
    def _update_preview_labels(self, *_args) -> None: update_preview_labels(self)
    def _start_render(self, target: Path, fmt: str, is_preview: bool) -> None: start_pitch_render(self, target, fmt, is_preview)
    def _on_rendered(self, path_str: str, is_preview: bool) -> None: handle_pitch_rendered(self, path_str, is_preview)
    def _open_export_folder(self) -> None: open_export_folder(self)
    def _export_name(self, fmt: str) -> str: return build_export_name(self, fmt)
    def _tempo_ratio(self) -> float: return compute_tempo_ratio(self)
    def _set_controls_enabled(self, enabled: bool) -> None: set_controls_enabled(self, enabled)
