"""Audio Tools page for Key/BPM estimation, Waveform, Camelot mix, Rubber Band R3, and export."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.services.audio_analysis import camelot_code, enharmonic_key, transpose_key
from src.services.audio_camelot import get_harmonic_neighbors
from src.services.audio_pitch import build_export_filename, unique_export_path
from src.services.platform_actions import open_parent, open_path
from src.ui.components.batch_audio_dialog import BatchAudioDialog
from src.ui.dialogs import get_open_file_path, get_open_files
from src.ui.i18n import tr
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals, PitchJob, RenderPitchWorker

from .audio_tools_presenter import format_analysis_status, populate_candidate_buttons, populate_harmonic_buttons
from .audio_tools_view import build_ui

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus);;All files (*.*)"


class AudioToolsInterface(QWidget):
    fileExported = pyqtSignal(str)
    analysisCompleted = pyqtSignal(dict)

    def __init__(self, config, historyManager=None, parent=None):
        super().__init__(parent)
        self._cfg, self._hist, self._source, self._lastExport = config, historyManager, None, None
        self._candidates, self._harmonic_cands, self._busy, self._pool = [], [], False, QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self.setAcceptDrops(True)
        build_ui(self)
        self._set_controls_enabled(False)

    def dragEnterEvent(self, event) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

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
        self.fileLabel.setText(f"{cand.name} ({cand.parent})")
        self._set_controls_enabled(True) or self._update_preview_labels()
        self._on_analyzed(cached) if (cached and cached.get("key")) else self._reanalyze()

    def _choose_file(self) -> None:
        if (sel := get_open_file_path(self, "Choose audio file", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))):
            self.loadFile(sel)

    def _open_batch_dialog(self) -> None:
        if (files := get_open_files(self, "Choose audio files for batch processing", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))):
            BatchAudioDialog(files, self._cfg, self, {str(self._source): self.detectedKeyCombo.currentText()} if self._source else {}).exec()

    def _reanalyze(self) -> None:
        if self._source and not self._busy:
            self._busy, self._signals = True, AudioToolSignals()
            self.statusLabel.setText("Analyzing Key, Waveform & BPM…")
            self._signals.analyzed.connect(self._on_analyzed) or self._signals.error.connect(self._on_error)
            self._pool.start(AnalyzeAudioWorker(self._source, self._signals))

    def _on_analyzed(self, result: dict) -> None:
        self._busy, key, bpm = False, str(result.get("key") or "C major"), float(result.get("bpm") or 120.0)
        self._candidates, self._harmonic_cands = list(result.get("key_candidates") or []), get_harmonic_neighbors(key)
        self.detectedKeyCombo.setCurrentText(key)
        self.bpmSpin.blockSignals(True) or self.bpmSpin.setValue(bpm) or self.bpmSpin.blockSignals(False)
        self.targetBpmSpin.setValue(bpm)
        self.badgeLabel.setText(str(result.get("badge") or "Experimental / Estimate"))
        self.sectionKeyLabel.setText(f"Section Key: {result.get('section_summary', '--')}")
        self.waveformWidget.setPeaks(result.get("peaks", []), result.get("duration_sec", 0.0), result.get("section_summary", ""))
        populate_candidate_buttons(self.candButtons, self._candidates, key) or populate_harmonic_buttons(self.camelotButtons, self._harmonic_cands)
        self._update_preview_labels() or self.statusLabel.setText(format_analysis_status(key, bpm, result))
        self.analysisCompleted.emit(result)

    def _select_candidate(self, i: int) -> None:
        0 <= i < len(self._candidates) and self.detectedKeyCombo.setCurrentText(str(self._candidates[i]["key"]))
    def _select_harmonic_neighbor(self, i: int) -> None:
        0 <= i < len(self._harmonic_cands) and self.semitoneSpin.setValue(self._harmonic_cands[i]["semitones"])
    def _on_source_bpm_changed(self, value: float) -> None:
        self.targetBpmSpin.setValue(value) or self._update_preview_labels()

    def _update_preview_labels(self, *_args) -> None:
        base_key, semitones = self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value()
        shifted_key, enh, ratio = transpose_key(base_key, semitones), enharmonic_key(base_key), self._tempo_ratio()
        self.camelotLabel.setText(f"Camelot: {camelot_code(base_key)}" + (f" ({enh})" if enh != base_key else ""))
        self.resultingKeyLabel.setText(f"Resulting key: {shifted_key} ({camelot_code(shifted_key)}) · {f'+{semitones}' if semitones > 0 else semitones} st")
        self.tempoRatioLabel.setText(f"Stretch: {ratio:.2f}x ({ratio * 100:.0f}%)")
        self._source and self.outputPreviewLabel.setText(f"Safe export copy: {self._export_name(str(self.formatCombo.currentData() or 'wav'))} (original untouched)")

    def _play_original(self) -> None:
        open_path(self._source) if (self._source and self._source.is_file()) else None

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
        self._signals.rendered.connect(self._on_rendered) or self._signals.error.connect(self._on_error)
        self._pool.start(RenderPitchWorker(PitchJob(self._source, target, self.semitoneSpin.value(), str(self.engineCombo.currentData() or "r3_finer"), fmt, is_preview, self._tempo_ratio()), self._signals))

    def _on_rendered(self, path_str: str, is_preview: bool) -> None:
        self._busy, out = False, Path(path_str)
        self.exportBtn.setEnabled(True)
        if is_preview:
            return self.statusLabel.setText(f"Playing shifted preview: {out.name}") or open_path(out)
        self._lastExport = out
        self.openFolderBtn.show() or self.statusLabel.setText(f"Exported: {out.name}")
        self._hist and out.is_file() and self._hist.addEntry("", out.stem, "audio", out.suffix.lstrip(".").upper(), str(out), True, out.stat().st_size, status="completed")
        self.fileExported.emit(str(out))

    def _on_error(self, message: str) -> None:
        self._busy = False
        self.exportBtn.setEnabled(bool(self._source)) or self.statusLabel.setText(message)

    def _open_export_folder(self) -> None:
        open_parent(self._lastExport) if (self._lastExport and self._lastExport.exists()) else None

    def _export_name(self, fmt: str) -> str:
        tb = self.targetBpmSpin.value() if abs(self._tempo_ratio() - 1.0) >= 0.005 else 0.0
        return build_export_filename(self._source, self.semitoneSpin.value(), transpose_key(self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value()), fmt, tb)

    def _tempo_ratio(self) -> float:
        return max(0.5, min(2.0, self.targetBpmSpin.value() / max(30.0, self.bpmSpin.value())))

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in (self.reanalyzeBtn, self.previewOrigBtn, self.previewShiftedBtn, self.exportBtn, *self.candButtons, *self.camelotButtons):
            w.setEnabled(enabled)
