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

from . import library_view
from .library_view import AUDIO_EXTS, build_library_ui, empty_message, find_cached_analysis, matches_entry, record_local_file, summary_text

_MEDIA_FILTER = "Media files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.webm);;All files (*.*)"


class LibraryInterface(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, historyManager, config=None, parent=None):
        super().__init__(parent)
        self._hist, self._cfg, self._lang = historyManager, config, "en"
        self._limit, self._analysisCache, self._cardsByPath, self._bgSignals = 50, {}, {}, []
        self._activeWorkers: list[AnalyzeAudioWorker] = []
        self._analysisPool, self._debounce = QThreadPool(self), QTimer(self, singleShot=True, interval=250)
        self._analysisPool.setMaxThreadCount(1)
        self._debounce.timeout.connect(self._apply_search)
        build_library_ui(self)
        self.refresh()

    def setLanguage(self, lang: str) -> None:
        self._lang = lang
        library_view.set_language(self, lang)
        entries, stats = self._filtered_entries(), self._hist.getStats()
        self.summary.setText(summary_text(stats, lang))
        self.emptyLabel.setText(empty_message(entries, stats, lang))
        for card in self._cardsByPath.values():
            card.setLanguage(lang)

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
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS and p.stat().st_size >= 100 and key not in self._analysisCache:
            signals = AudioToolSignals()
            worker = AnalyzeAudioWorker(p, signals)
            signals.analyzed.connect(lambda res, s=signals, w=worker: (self._cleanup_bg_job(s, w), self.storeAnalysisResult(res)))
            signals.error.connect(lambda _err, s=signals, w=worker: self._cleanup_bg_job(s, w))
            self._bgSignals.append(signals)
            self._activeWorkers.append(worker)
            self._analysisPool.start(worker)

    def _cleanup_bg_job(self, sig: AudioToolSignals, worker: AnalyzeAudioWorker) -> None:
        sig in self._bgSignals and self._bgSignals.remove(sig)
        worker in self._activeWorkers and self._activeWorkers.remove(worker)

    def storeAnalysisResult(self, result: dict) -> None:
        if not (fp := str(result.get("filePath") or "")):
            return
        self._analysisCache.pop(fp, None)
        while len(self._analysisCache) >= 200:
            self._analysisCache.pop(next(iter(self._analysisCache)), None)
        self._analysisCache[fp] = result
        getattr(self._hist, "updateAnalysis", lambda *_: None)(fp, result)
        fp in self._cardsByPath and self._cardsByPath[fp].setAnalysisResult(result)

    def cleanup(self) -> None:
        for worker in list(self._activeWorkers):
            getattr(worker, "cancel", lambda: None)()
        self._analysisPool.clear()
        self._analysisPool.waitForDone(2000)
        self._bgSignals.clear()
        self._activeWorkers.clear()

    def getCachedAnalysis(self, file_path: str) -> dict | None:
        return find_cached_analysis(self._analysisCache, file_path)

    def refresh(self, *_args) -> None:
        for e in self._hist.getHistory(200):
            if (fp := str(e.get("filePath") or "")) and isinstance(e.get("analysis"), dict) and e["analysis"].get("key"):
                self._analysisCache.setdefault(fp, e["analysis"])
        while len(self._analysisCache) > 200:
            self._analysisCache.pop(next(iter(self._analysisCache)), None)
        entries, stats = self._filtered_entries(), self._hist.getStats()
        visible = entries[:self._limit]
        self._clear_cards()
        for entry in visible:
            fp = str(entry.get("filePath") or "")
            card = LibraryCard(entry, self._analysisCache.get(fp))
            card.setLanguage(self._lang)
            card.redownloadRequested.connect(self.redownloadRequested.emit)
            card.openInAudioToolsRequested.connect(self.openInAudioToolsRequested.emit)
            if fp:
                self._cardsByPath[fp] = card
            self.listLay.insertWidget(self.listLay.count() - 1, card)
        self.summary.setText(summary_text(stats, self._lang))
        self.emptyLabel.setText(empty_message(entries, stats, self._lang))
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
        t, m, b = tr("lib.clear_confirm_title", self._lang), tr("lib.clear_confirm_msg", self._lang), tr("lib.btn_clear", self._lang)
        if MessageBox(t, m, self, b).exec():
            self._hist.clearHistory() or self._apply_search()
