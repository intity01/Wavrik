"""Audio Tools page for Key/BPM estimation, Rubber Band R3 pitch/tempo shift, and export."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.services.audio_analysis import camelot_code, enharmonic_key, mirex_key_score, transpose_key
from src.services.audio_pitch import build_export_filename, unique_export_path
from src.services.platform_actions import open_parent, open_path
from src.ui.dialogs import get_open_file_path
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals, PitchJob, RenderPitchWorker
from .audio_tools_view import build_ui

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus);;All files (*.*)"


class AudioToolsInterface(QWidget):
    fileExported = pyqtSignal(str)
    analysisCompleted = pyqtSignal(dict)

    def __init__(self, config, historyManager=None, parent=None):
        super().__init__(parent)
        self._cfg, self._hist, self._source, self._lastExport = config, historyManager, None, None
        self._candidates, self._busy, self._pool = [], False, QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        build_ui(self)
        self._set_controls_enabled(False)

    def loadFile(self, path: str | Path, cached: dict | None = None) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            self.statusLabel.setText("Selected audio file does not exist.")
            return
        self._source = candidate
        self.fileLabel.setText(f"{candidate.name} ({candidate.parent})")
        self._set_controls_enabled(True)
        self._update_preview_labels()
        self._on_analyzed(cached) if (cached and cached.get("key")) else self._reanalyze()

    def _choose_file(self) -> None:
        if (sel := get_open_file_path(self, "Choose audio file", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))):
            self.loadFile(sel)

    def _reanalyze(self) -> None:
        if self._source and not self._busy:
            self._busy, self._signals = True, AudioToolSignals()
            self.statusLabel.setText("Analyzing Key, Section Modulation & BPM…")
            self._signals.analyzed.connect(self._on_analyzed)
            self._signals.error.connect(self._on_error)
            self._pool.start(AnalyzeAudioWorker(self._source, self._signals))

    def _on_analyzed(self, result: dict) -> None:
        self._busy, key, bpm = False, str(result.get("key") or "C major"), float(result.get("bpm") or 120.0)
        self._candidates = list(result.get("key_candidates") or [])
        self.detectedKeyCombo.setCurrentText(key)
        self.bpmSpin.blockSignals(True)
        self.bpmSpin.setValue(bpm)
        self.bpmSpin.blockSignals(False)
        self.targetBpmSpin.setValue(bpm)
        self.badgeLabel.setText(str(result.get("badge") or "Experimental / Estimate"))
        self.sectionKeyLabel.setText(f"Section Key: {result.get('section_summary', '--')}")
        _populate_candidate_buttons(self.candButtons, self._candidates, key)
        self._update_preview_labels()
        self.statusLabel.setText(_format_analysis_status(key, bpm, result))
        self.analysisCompleted.emit(result)

    def _select_candidate(self, index: int) -> None:
        if 0 <= index < len(self._candidates):
            self.detectedKeyCombo.setCurrentText(str(self._candidates[index]["key"]))

    def _on_source_bpm_changed(self, value: float) -> None:
        self.targetBpmSpin.setValue(value)
        self._update_preview_labels()

    def _update_preview_labels(self, *_args) -> None:
        base_key, semitones = self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value()
        shifted_key, enh, ratio = transpose_key(base_key, semitones), enharmonic_key(base_key), self._tempo_ratio()
        self.camelotLabel.setText(f"Camelot: {camelot_code(base_key)}" + (f" ({enh})" if enh != base_key else ""))
        self.resultingKeyLabel.setText(f"Resulting key: {shifted_key} ({camelot_code(shifted_key)}) · {f'+{semitones}' if semitones > 0 else semitones} st")
        self.tempoRatioLabel.setText(f"Stretch: {ratio:.2f}x ({ratio * 100:.0f}%)")
        if self._source:
            self.outputPreviewLabel.setText(f"Safe export copy: {self._export_name(str(self.formatCombo.currentData() or 'wav'))} (original untouched)")

    def _play_original(self) -> None:
        open_path(self._source) if (self._source and self._source.is_file()) else None

    def _preview_shifted(self) -> None:
        if self._source and not self._busy:
            preview_dir = Path(tempfile.gettempdir()) / "WavrikPreview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            self._start_render(unique_export_path(preview_dir, self._export_name("wav")), "wav", True)

    def _export_shifted(self) -> None:
        if self._source and not self._busy:
            fmt = str(self.formatCombo.currentData() or "wav")
            self._start_render(unique_export_path(self._cfg.getDownloadPath("audio"), self._export_name(fmt)), fmt, False)

    def _start_render(self, target: Path, fmt: str, is_preview: bool) -> None:
        self._busy, self._signals = True, AudioToolSignals()
        self.statusLabel.setText("Rendering audio with Rubber Band…")
        self.exportBtn.setEnabled(False)
        self._signals.rendered.connect(self._on_rendered)
        self._signals.error.connect(self._on_error)
        self._pool.start(RenderPitchWorker(PitchJob(self._source, target, self.semitoneSpin.value(), str(self.engineCombo.currentData() or "r3_finer"), fmt, is_preview, self._tempo_ratio()), self._signals))

    def _on_rendered(self, path_str: str, is_preview: bool) -> None:
        self._busy, out = False, Path(path_str)
        self.exportBtn.setEnabled(True)
        if is_preview:
            self.statusLabel.setText(f"Playing shifted preview: {out.name}")
            return open_path(out)
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
        open_parent(self._lastExport) if (self._lastExport and self._lastExport.exists()) else None

    def _export_name(self, fmt: str) -> str:
        tbpm = self.targetBpmSpin.value() if abs(self._tempo_ratio() - 1.0) >= 0.005 else 0.0
        return build_export_filename(self._source, self.semitoneSpin.value(), transpose_key(self.detectedKeyCombo.currentText() or "C major", self.semitoneSpin.value()), fmt, tbpm)

    def _tempo_ratio(self) -> float:
        return max(0.5, min(2.0, self.targetBpmSpin.value() / max(30.0, self.bpmSpin.value())))

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in (self.reanalyzeBtn, self.previewOrigBtn, self.previewShiftedBtn, self.exportBtn, *self.candButtons):
            w.setEnabled(enabled)
def _populate_candidate_buttons(buttons: list, candidates: list[dict], top_key: str) -> None:
    for idx, btn in enumerate(buttons):
        ck = str(candidates[idx]["key"]) if idx < len(candidates) else ""
        btn.setText(f"#{idx + 1} {ck} ({camelot_code(ck)} · {mirex_key_score(ck, top_key)[1] if idx > 0 else 'Top'})" if ck else f"#{idx + 1} --")
def _format_analysis_status(key: str, bpm: float, result: dict) -> str:
    enh, conf = enharmonic_key(key), result.get("confidence", "")
    return f"Estimated {f'{key} / {enh}' if enh != key else key} ({camelot_code(key)}){f' [{conf}%]' if conf else ''} · {bpm:.1f} BPM"
