"""Audio Tools page for Key/BPM estimation, Rubber Band R3 pitch shift, and export."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.services.audio_analysis import camelot_code, transpose_key
from src.services.audio_pitch import build_export_filename, unique_export_path
from src.services.platform_actions import open_parent, open_path
from src.ui.dialogs import get_open_file_path
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals, PitchJob, RenderPitchWorker

from .audio_tools_view import build_ui

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus);;All files (*.*)"


class AudioToolsInterface(QWidget):
    fileExported = pyqtSignal(str)

    def __init__(self, config, historyManager=None, parent=None):
        super().__init__(parent)
        self._cfg, self._hist = config, historyManager
        self._source: Path | None = None
        self._lastExport: Path | None = None
        self._busy = False
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        build_ui(self)
        self._set_controls_enabled(False)

    def loadFile(self, path: str | Path) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            self.statusLabel.setText("Selected audio file does not exist.")
            return
        self._source = candidate
        self.fileLabel.setText(f"{candidate.name} ({candidate.parent})")
        self._set_controls_enabled(True)
        self._update_preview_labels()
        self._reanalyze()

    def _choose_file(self) -> None:
        selected = get_open_file_path(self, "Choose audio file", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))
        if selected:
            self.loadFile(selected)

    def _reanalyze(self) -> None:
        if not self._source or self._busy:
            return
        self._busy = True
        self.statusLabel.setText("Analyzing Key & BPM (CPU estimate)…")
        signals = AudioToolSignals()
        signals.analyzed.connect(self._on_analyzed)
        signals.error.connect(self._on_error)
        self._signals = signals
        self._pool.start(AnalyzeAudioWorker(self._source, signals))

    def _on_analyzed(self, result: dict) -> None:
        self._busy = False
        key, bpm = str(result.get("key") or "C major"), float(result.get("bpm") or 120.0)
        self.detectedKeyCombo.setCurrentText(key)
        self.bpmSpin.setValue(bpm)
        self._update_preview_labels()
        self.statusLabel.setText(f"Estimated {key} ({camelot_code(key)}) · {bpm:.1f} BPM")

    def _update_preview_labels(self, *_args) -> None:
        base_key, semitones = self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value()
        shifted_key = transpose_key(base_key, semitones)
        self.camelotLabel.setText(f"Camelot: {camelot_code(base_key)}")
        sign = f"+{semitones}" if semitones > 0 else str(semitones)
        self.resultingKeyLabel.setText(f"Resulting key: {shifted_key} ({camelot_code(shifted_key)}) · {sign} st")
        if self._source:
            name = build_export_filename(self._source, semitones, shifted_key, str(self.formatCombo.currentData() or "wav"))
            self.outputPreviewLabel.setText(f"Safe export copy: {name} (original untouched)")

    def _play_original(self) -> None:
        if self._source and self._source.is_file():
            open_path(self._source)

    def _preview_shifted(self) -> None:
        if not self._source or self._busy:
            return
        preview_dir = Path(tempfile.gettempdir()) / "WavrikPreview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        target = unique_export_path(preview_dir, build_export_filename(self._source, self.semitoneSpin.value(), self._target_key(), "wav"))
        self._start_render(target, "wav", is_preview=True)

    def _export_shifted(self) -> None:
        if not self._source or self._busy:
            return
        fmt = str(self.formatCombo.currentData() or "wav")
        filename = build_export_filename(self._source, self.semitoneSpin.value(), self._target_key(), fmt)
        self._start_render(unique_export_path(self._cfg.getDownloadPath("audio"), filename), fmt, is_preview=False)

    def _start_render(self, target: Path, fmt: str, is_preview: bool) -> None:
        if not self._source:
            return
        self._busy = True
        self.statusLabel.setText("Rendering pitch-shifted audio…")
        self.exportBtn.setEnabled(False)
        signals = AudioToolSignals()
        signals.rendered.connect(self._on_rendered)
        signals.error.connect(self._on_error)
        self._signals = signals
        job = PitchJob(self._source, target, self.semitoneSpin.value(), str(self.engineCombo.currentData() or "r3_finer"), fmt, is_preview)
        self._pool.start(RenderPitchWorker(job, signals))

    def _on_rendered(self, path_str: str, is_preview: bool) -> None:
        self._busy, out = False, Path(path_str)
        self.exportBtn.setEnabled(True)
        if is_preview:
            self.statusLabel.setText(f"Playing shifted preview: {out.name}")
            open_path(out)
            return
        self._lastExport = out
        self.openFolderBtn.show()
        self.statusLabel.setText(f"Exported: {out.name}")
        if self._hist and out.is_file():
            self._hist.addEntry("", out.stem, "audio", out.suffix.lstrip(".").upper(), str(out), True, out.stat().st_size, status="completed")
        self.fileExported.emit(str(out))

    def _on_error(self, message: str) -> None:
        self._busy = False
        self.exportBtn.setEnabled(bool(self._source))
        self.statusLabel.setText(message)

    def _open_export_folder(self) -> None:
        if self._lastExport and self._lastExport.exists():
            open_parent(self._lastExport)

    def _target_key(self) -> str:
        return transpose_key(self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value())

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in (self.reanalyzeBtn, self.previewOrigBtn, self.previewShiftedBtn, self.exportBtn):
            widget.setEnabled(enabled)
