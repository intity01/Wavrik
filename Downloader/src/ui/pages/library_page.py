"""Unified searchable media library with compact table rows and background Key/BPM analysis."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.ui.components.controls import MessageBox
from src.ui.components.library_card import LibraryCard
from src.ui.dialogs import get_open_file_path
from src.ui.i18n import tr
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals

from .library_view import AUDIO_EXTS, build_library_ui, empty_message, matches_entry, record_local_file, summary_text

_MEDIA_FILTER = "Media files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.webm);;All files (*.*)"


class LibraryInterface(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, historyManager, config=None, parent=None):
        super().__init__(parent)
        self._hist, self._cfg = historyManager, config
        self._limit, self._analysisCache, self._cardsByPath, self._bgSignals = 50, {}, {}, []
        self._analysisPool, self._debounce = QThreadPool(self), QTimer(self, singleShot=True, interval=250)
        self._analysisPool.setMaxThreadCount(1)
        self._debounce.timeout.connect(self._apply_search)
        build_library_ui(self)
        self.refresh()

    def setLanguage(self, lang: str) -> None:
        self.titleLabel.setText(tr("lib.title", lang))
        self.subtitleLabel.setText(tr("lib.subtitle", lang))
        self.searchBar.setPlaceholderText(tr("lib.search_placeholder", lang))
        self.colTrack.setText(tr("lib.col_track", lang))
        self.colHarmony.setText(tr("lib.col_harmony", lang))
        self.colStatus.setText(tr("lib.col_status", lang))
        self.colActions.setText(tr("lib.col_actions", lang))

    def _apply_search(self) -> None:
        self._limit = 50
        self.refresh()

    def _load_more(self) -> None:
        self._limit += 50
        self.refresh()

    def _add_local(self) -> None:
        if (sel := get_open_file_path(self, "Add local media file", _MEDIA_FILTER)) and sel.is_file():
            record_local_file(self._hist, sel)
            self.refresh()
            self.enqueueAutoAnalyze(str(sel))

    def enqueueAutoAnalyze(self, file_path: str) -> None:
        p, key = Path(file_path), str(Path(file_path))
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS and key not in self._analysisCache:
            signals = AudioToolSignals()
            signals.analyzed.connect(self.storeAnalysisResult)
            self._bgSignals.append(signals)
            self._analysisPool.start(AnalyzeAudioWorker(p, signals))

    def storeAnalysisResult(self, result: dict) -> None:
        if (fp := str(result.get("filePath") or "")):
            self._analysisCache[fp] = result
            if hasattr(self._hist, "updateAnalysis"):
                self._hist.updateAnalysis(fp, result)
            if fp in self._cardsByPath:
                self._cardsByPath[fp].setAnalysisResult(result)

    def getCachedAnalysis(self, file_path: str) -> dict | None:
        return self._analysisCache.get(str(Path(file_path)))

    def refresh(self, *_args) -> None:
        for e in self._hist.getHistory(1000):
            if (fp := str(e.get("filePath") or "")) and isinstance(e.get("analysis"), dict) and e["analysis"].get("key"):
                self._analysisCache.setdefault(fp, e["analysis"])
        entries, stats = self._filtered_entries(), self._hist.getStats()
        visible = entries[:self._limit]
        self._clear_cards()
        for entry in visible:
            fp = str(entry.get("filePath") or "")
            card = LibraryCard(entry, self._analysisCache.get(fp))
            card.redownloadRequested.connect(self.redownloadRequested.emit)
            card.openInAudioToolsRequested.connect(self.openInAudioToolsRequested.emit)
            if fp:
                self._cardsByPath[fp] = card
            self.listLay.insertWidget(self.listLay.count() - 1, card)
        self.summary.setText(summary_text(stats))
        self.emptyLabel.setText(empty_message(entries, stats))
        self.emptyLabel.setVisible(not entries)
        self.tableHeader.setVisible(bool(entries))
        self.scrollArea.setVisible(bool(entries))
        self.loadMoreBtn.setVisible(len(entries) > len(visible))

    def _filtered_entries(self) -> list[dict]:
        q = self.searchBar.text().casefold().strip()
        m = {1: "audio", 2: "video"}.get(self.typeFilter.currentIndex())
        s = {1: "completed", 2: "failed", 3: "cancelled"}.get(self.statusFilter.currentIndex())
        return [e for e in self._hist.getHistory(1000) if matches_entry(e, q, m, s, self._analysisCache)]

    def _clear_cards(self) -> None:
        self._cardsByPath.clear()
        while self.listLay.count() > 1:
            (w := self.listLay.takeAt(0).widget()) and w.deleteLater()

    def _clear(self) -> None:
        if MessageBox("Clear library", "This removes library records only. Media files on disk will not be deleted.", self, "Clear library").exec():
            self._hist.clearHistory() or self._apply_search()
