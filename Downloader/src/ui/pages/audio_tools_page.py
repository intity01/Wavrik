"""Audio Tools page for Key/BPM estimation, Waveform, Stem Separation, Rubber Band R3, and export."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.ui.components.audio_transport import AudioTransportController
from src.ui.components.batch_audio_dialog import BatchAudioDialog
from src.ui.dialogs import get_open_file_path, get_open_files
from src.ui.i18n import tr

from .audio_tools_jobs import AnalysisJobsMixin
from .audio_tools_playback import PlaybackActionsMixin
from .audio_tools_presenter import start_stem_separation
from .audio_tools_stems import audition_stem, load_stem, reset_stem_controls
from .audio_tools_view import build_ui

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus);;All files (*.*)"


class AudioToolsInterface(AnalysisJobsMixin, PlaybackActionsMixin, QWidget):
    fileExported = pyqtSignal(str)
    analysisCompleted = pyqtSignal(dict)

    def __init__(self, config, historyManager=None, parent=None):
        super().__init__(parent)
        self._cfg, self._hist = config, historyManager
        self._source: Path | None = None
        self._lastExport: Path | None = None
        self._candidates: list[dict] = []
        self._harmonic_cands: list[dict] = []
        self._busy = False
        self._signals = None
        self._activeWorker = None
        self._batchDialog = None
        self._clear_stems()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self.transport = AudioTransportController(self)
        self.setAcceptDrops(True)
        build_ui(self)
        self.transport.positionChanged.connect(self.waveformWidget.setSeekPosition)
        self._set_controls_enabled(False)

    def _text(self, key: str) -> str:
        return tr(key, getattr(self, "_lang", "en"))

    def _clear_stems(self) -> None:
        self._vocalsStem = self._drumsStem = self._bassStem = self._otherStem = self._instStem = None

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).is_file():
                self.loadFile(Path(url.toLocalFile()))
                return

    def setLanguage(self, lang: str) -> None:
        from .audio_tools_i18n import set_language
        set_language(self, lang)

    def loadFile(self, path: str | Path, cached: dict | None = None) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            self.statusLabel.setText(self._text("at.file_not_exist"))
            return
        self._discard_active_job()
        self._source, self._busy = candidate, False
        self._clear_stems()
        reset_stem_controls(self)
        self.transport.setSlotA(candidate)
        self.fileLabel.setText(f"{candidate.name} ({candidate.parent})")
        self._set_controls_enabled(True)
        self._update_preview_labels()
        if result := self._cached_analysis(candidate, cached):
            self._on_analyzed(result)
        else:
            self._reanalyze()


    def _choose_file(self) -> None:
        selected = get_open_file_path(self, "Choose audio file", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))
        if selected:
            self.loadFile(selected)

    def _open_batch_dialog(self) -> None:
        files = get_open_files(self, "Choose audio files for batch processing", _AUDIO_FILTER, self._cfg.get("downloadPath", ""))
        if not files:
            return
        known_keys = {str(self._source): self.detectedKeyCombo.currentText()} if self._source else {}
        self._batchDialog = BatchAudioDialog(files, self._cfg, self, known_keys)
        self._batchDialog.exec()
        self._batchDialog = None

    def _open_tag_dialog(self) -> None:
        if self._source and self._source.is_file():
            from src.ui.components.audio_tag_dialog import AudioTagDialog
            AudioTagDialog(self._source, self).exec()


    def _select_candidate(self, index: int) -> None:
        if 0 <= index < len(self._candidates):
            self.detectedKeyCombo.setCurrentText(str(self._candidates[index]["key"]))

    def _select_harmonic_neighbor(self, index: int) -> None:
        if 0 <= index < len(self._harmonic_cands):
            self.semitoneSpin.setValue(self._harmonic_cands[index]["semitones"])

    def _on_source_bpm_changed(self, value: float) -> None:
        self.waveformWidget.setBpm(value)
        self.targetBpmSpin.setValue(value)
        self._update_preview_labels()

    def cleanup(self) -> None:
        self._busy = False
        self.transport.stop()
        self._discard_active_job()
        if self._batchDialog is not None and hasattr(self._batchDialog, "_cancel_and_wait"):
            self._batchDialog._cancel_and_wait()
        self._pool.clear()
        self._pool.waitForDone(2000)

    def _separate_stems(self) -> None: start_stem_separation(self)
    def _load_stem(self, stem: str) -> None: load_stem(self, stem)
    def _audition_stem(self, stem: str) -> None: audition_stem(self, stem)
    def _load_vocals_stem(self) -> None: self._load_stem("vocals")
    def _load_inst_stem(self) -> None: self._load_stem("inst")
