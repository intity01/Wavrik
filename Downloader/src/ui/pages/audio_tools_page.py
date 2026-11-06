"""Audio Tools page for Key/BPM estimation, Waveform, Stem Separation, Rubber Band R3, and export."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.services.audio_pitch import unique_export_path
from src.ui.components.audio_transport import AudioTransportController
from src.ui.components.batch_audio_dialog import BatchAudioDialog
from src.ui.dialogs import get_open_file_path, get_open_files
from src.ui.i18n import tr
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals, PitchJob, RenderPitchWorker

from .audio_tools_presenter import (
    apply_analysis_result, build_export_name, compute_tempo_ratio,
    open_export_folder, set_controls_enabled, start_stem_separation, update_preview_labels,
)
from .audio_tools_view import build_ui

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus);;All files (*.*)"


class AudioToolsInterface(QWidget):
    fileExported = pyqtSignal(str)
    analysisCompleted = pyqtSignal(dict)

    def __init__(self, config, historyManager=None, parent=None):
        super().__init__(parent)
        self._cfg, self._hist, self._source, self._lastExport, self._vocalsStem, self._instStem = config, historyManager, None, None, None, None
        self._candidates, self._harmonic_cands, self._busy, self._pool = [], [], False, QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self.transport = AudioTransportController(self)
        self.setAcceptDrops(True)
        build_ui(self)
        self._set_controls_enabled(False)

    def dragEnterEvent(self, event) -> None: event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()
    def dropEvent(self, event) -> None:
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile() and Path(u.toLocalFile()).is_file()]
        files and self.loadFile(files[0])
    def setLanguage(self, lang: str) -> None:
        self.titleLabel.setText(tr("at.title", lang)) or self.subtitleLabel.setText(tr("at.subtitle", lang))
        not self._source and self.fileLabel.setText(tr("at.no_file", lang))
    def loadFile(self, path: str | Path, cached: dict | None = None) -> None:
        if not (cand := Path(path)).is_file():
            return self.statusLabel.setText("Selected audio file does not exist.")
        self._source, self._busy = cand, False
        self.transport.setSlotA(cand) or self.fileLabel.setText(f"{cand.name} ({cand.parent})")
        self._set_controls_enabled(True) or self._update_preview_labels()
        hit = cached if (cached and cached.get("key")) else (self._hist.getCachedAnalysis(cand) if (self._hist and hasattr(self._hist, "getCachedAnalysis")) else None)
        self._on_analyzed(hit) if hit else self._reanalyze()
    def _choose_file(self) -> None:
        (sel := get_open_file_path(self, "Choose audio file", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))) and self.loadFile(sel)
    def _open_batch_dialog(self) -> None:
        if (files := get_open_files(self, "Choose audio files for batch processing", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))):
            self._batchDialog = BatchAudioDialog(files, self._cfg, self, {str(self._source): self.detectedKeyCombo.currentText()} if self._source else {})
            self._batchDialog.exec()
            self._batchDialog = None

    def _reanalyze(self) -> None:
        if self._source and not self._busy:
            self._busy, self._signals = True, AudioToolSignals()
            self.statusLabel.setText("Analyzing Key, Waveform & BPM…")
            self._signals.analyzed.connect(self._on_analyzed)
            self._signals.error.connect(self._on_error)
            self._activeWorker = AnalyzeAudioWorker(self._source, self._signals)
            self._pool.start(self._activeWorker)

    def _on_analyzed(self, result: dict) -> None:
        self._busy = False
        self._hist and self._source and hasattr(self._hist, "updateAnalysis") and self._hist.updateAnalysis(str(self._source), result)
        apply_analysis_result(self, result)
        self.analysisCompleted.emit(result)

    def _select_candidate(self, i: int) -> None:
        0 <= i < len(self._candidates) and self.detectedKeyCombo.setCurrentText(str(self._candidates[i]["key"]))
    def _select_harmonic_neighbor(self, i: int) -> None:
        0 <= i < len(self._harmonic_cands) and self.semitoneSpin.setValue(self._harmonic_cands[i]["semitones"])
    def _on_source_bpm_changed(self, value: float) -> None:
        self.targetBpmSpin.setValue(value) or self._update_preview_labels()
    def _separate_stems(self) -> None: start_stem_separation(self)
    def _load_vocals_stem(self) -> None: self._vocalsStem and self._vocalsStem.is_file() and self.loadFile(self._vocalsStem)
    def _load_inst_stem(self) -> None: self._instStem and self._instStem.is_file() and self.loadFile(self._instStem)
    def _on_seek_requested(self, sec: float) -> None:
        self.statusLabel.setText(f"Playhead set to {int(sec // 60)}:{int(sec % 60):02d} (25s preview slice)")
        self.transport.isPlaying() and self.transport.playSlot(self.transport.activeSlot(), sec)
    def _update_preview_labels(self, *_args) -> None:
        update_preview_labels(self)
    def _play_original(self) -> None:
        if self._source and self._source.is_file():
            self.transport.playSlot("A", self.waveformWidget.seekPosition())
            self.statusLabel.setText(f"Playing Original (A): {self._source.name}")
    def _stop_playback(self) -> None:
        self.transport.stop() or self.statusLabel.setText("Playback stopped.")
    def _preview_shifted(self) -> None:
        if self._source and not self._busy:
            (d := Path(tempfile.gettempdir()) / "WavrikPreview").mkdir(parents=True, exist_ok=True)
            self._start_render(unique_export_path(d, self._export_name("wav")), "wav", True)
    def _export_shifted(self) -> None:
        if self._source and not self._busy:
            self._start_render(unique_export_path(self._cfg.getDownloadPath("audio"), self._export_name(fmt := str(self.formatCombo.currentData() or "wav"))), fmt, False)

    def _start_render(self, target: Path, fmt: str, is_preview: bool) -> None:
        self._busy, self._signals = True, AudioToolSignals()
        self.statusLabel.setText("Rendering audio with Rubber Band…") or self.exportBtn.setEnabled(False)
        self._signals.rendered.connect(self._on_rendered)
        self._signals.error.connect(self._on_error)
        job = PitchJob(self._source, target, self.semitoneSpin.value(), str(self.engineCombo.currentData() or "r3_finer"), fmt, is_preview, self._tempo_ratio(), self.waveformWidget.seekPosition())
        self._activeWorker = RenderPitchWorker(job, self._signals)
        self._pool.start(self._activeWorker)

    def _on_rendered(self, path_str: str, is_preview: bool) -> None:
        self._busy, out = False, Path(path_str)
        self.exportBtn.setEnabled(True)
        if is_preview:
            self.transport.setSlotB(out) or self.transport.playSlot("B")
            return self.statusLabel.setText(f"Playing Shifted Preview (B): {out.name}")
        self._lastExport = out
        self.openFolderBtn.show() or self.statusLabel.setText(f"Exported: {out.name}")
        self._hist and out.is_file() and self._hist.addEntry("", out.stem, "audio", out.suffix.lstrip(".").upper(), str(out), True, out.stat().st_size, status="completed")
        self.fileExported.emit(str(out))

    def _on_error(self, message: str) -> None:
        self._busy = False
        self.separateStemsBtn.setEnabled(bool(self._source))
        self.exportBtn.setEnabled(bool(self._source))
        self.statusLabel.setText(message)

    def cleanup(self) -> None:
        self._busy = False
        getattr(self, "_activeWorker", None) and hasattr(self._activeWorker, "cancel") and self._activeWorker.cancel()
        getattr(self, "_batchDialog", None) and hasattr(self._batchDialog, "_cancel_and_wait") and self._batchDialog._cancel_and_wait()
        self._pool.clear()
        self._pool.waitForDone(2000)

    def _open_export_folder(self) -> None: open_export_folder(self)
    def _export_name(self, fmt: str) -> str: return build_export_name(self, fmt)
    def _tempo_ratio(self) -> float: return compute_tempo_ratio(self)
    def _set_controls_enabled(self, enabled: bool) -> None: set_controls_enabled(self, enabled)
