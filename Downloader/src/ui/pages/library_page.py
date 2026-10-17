"""Unified searchable media library with background Key/BPM auto-analysis."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThreadPool, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, DangerPushButton, LineEdit, MessageBox, PushButton, SmoothScrollArea
from src.ui.components.library_card import LibraryCard
from src.ui.dialogs import get_open_file_path
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
_MEDIA_FILTER = "Media files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.webm);;All files (*.*)"


class LibraryInterface(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, historyManager, parent=None):
        super().__init__(parent)
        self._hist, self._limit, self._analysisCache, self._cardsByPath, self._bgSignals = historyManager, 50, {}, {}, []
        self._analysisPool, self._debounce = QThreadPool(self), QTimer(self, singleShot=True, interval=250)
        self._analysisPool.setMaxThreadCount(1)
        self._debounce.timeout.connect(self._apply_search)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        self.summary = QLabel(objectName="MutedText")
        for item in (self._build_header(), self._build_filters()):
            root.addLayout(item)
        root.addWidget(self.summary)
        self._build_list(root)
        self.refresh()

    def _build_header(self) -> QHBoxLayout:
        header, labels = QHBoxLayout(), QVBoxLayout()
        labels.addWidget(QLabel("Library", objectName="PageTitle"))
        labels.addWidget(QLabel("Search downloaded tracks and local files, auto-detect Key & BPM, or send to Audio Tools.", objectName="PageSubtitle"))
        self.addLocalBtn, clear = PushButton("Add local file"), DangerPushButton("Clear library")
        self.addLocalBtn.clicked.connect(self._add_local)
        clear.clicked.connect(self._clear)
        header.addLayout(labels, 1)
        for w in (self.addLocalBtn, clear):
            header.addWidget(w)
        return header

    def _build_filters(self) -> QHBoxLayout:
        filters = QHBoxLayout()
        self.searchBar, self.typeFilter, self.statusFilter = LineEdit(placeholderText="Search title, file name, Key (e.g. F# minor, 11A), or BPM"), ComboBox(), ComboBox()
        self.typeFilter.addItems(["All media", "Audio", "Video"])
        self.statusFilter.addItems(["All statuses", "Completed", "Failed", "Cancelled"])
        self.searchBar.textChanged.connect(self._debounce.start)
        self.typeFilter.currentIndexChanged.connect(self._apply_search)
        self.statusFilter.currentIndexChanged.connect(self._apply_search)
        for w, stretch in ((self.searchBar, 1), (self.typeFilter, 0), (self.statusFilter, 0)):
            filters.addWidget(w, stretch)
        return filters

    def _build_list(self, root: QVBoxLayout) -> None:
        self.scrollArea, self.scrollContent = SmoothScrollArea(), QWidget()
        self.scrollArea.setWidgetResizable(True)
        self.listLay = QVBoxLayout(self.scrollContent)
        self.listLay.setContentsMargins(0, 0, 0, 0)
        self.listLay.setSpacing(10)
        self.listLay.addStretch(1)
        self.scrollArea.setWidget(self.scrollContent)
        self.loadMoreBtn, self.emptyLabel = PushButton("Load more"), QLabel(objectName="MutedText")
        self.loadMoreBtn.clicked.connect(self._load_more)
        self.loadMoreBtn.hide()
        for w, stretch in ((self.scrollArea, 1), (self.loadMoreBtn, 0), (self.emptyLabel, 0)):
            root.addWidget(w, stretch)

    def _apply_search(self) -> None:
        self._limit = 50
        self.refresh()

    def _load_more(self) -> None:
        self._limit += 50
        self.refresh()

    def _add_local(self) -> None:
        if (sel := get_open_file_path(self, "Add local media file", _MEDIA_FILTER)) and sel.is_file():
            _record_local_file(self._hist, sel)
            self.refresh()
            self.enqueueAutoAnalyze(str(sel))

    def enqueueAutoAnalyze(self, file_path: str) -> None:
        p, key = Path(file_path), str(Path(file_path))
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTS and key not in self._analysisCache:
            signals = AudioToolSignals()
            signals.analyzed.connect(self.storeAnalysisResult)
            self._bgSignals.append(signals)
            self._analysisPool.start(AnalyzeAudioWorker(p, signals))

    def storeAnalysisResult(self, result: dict) -> None:
        if (fp := str(result.get("filePath") or "")):
            self._analysisCache[fp] = result
            if fp in self._cardsByPath:
                self._cardsByPath[fp].setAnalysisResult(result)

    def getCachedAnalysis(self, file_path: str) -> dict | None:
        return self._analysisCache.get(str(Path(file_path)))

    def refresh(self, *_args) -> None:
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
        self.summary.setText(_summary_text(stats))
        self.emptyLabel.setText(_empty_message(entries, stats))
        self.emptyLabel.setVisible(not entries)
        self.scrollArea.setVisible(bool(entries))
        self.loadMoreBtn.setVisible(len(entries) > len(visible))

    def _filtered_entries(self) -> list[dict]:
        q, m, s = self.searchBar.text().casefold().strip(), {1: "audio", 2: "video"}.get(self.typeFilter.currentIndex()), {1: "completed", 2: "failed", 3: "cancelled"}.get(self.statusFilter.currentIndex())
        return [e for e in self._hist.getHistory(1000) if _matches(e, q, m, s, self._analysisCache)]

    def _clear_cards(self) -> None:
        self._cardsByPath.clear()
        while self.listLay.count() > 1:
            (w := self.listLay.takeAt(0).widget()) and w.deleteLater()

    def _clear(self) -> None:
        if MessageBox("Clear library", "This removes library records only. Media files on disk will not be deleted.", self, "Clear library").exec():
            self._hist.clearHistory() or self._apply_search()
def _record_local_file(history_manager, path: Path) -> None:
    history_manager.addEntry("", path.stem, "video" if path.suffix.lower() in _VIDEO_EXTS else "audio", path.suffix.lstrip(".").upper() or "FILE", str(path), True, path.stat().st_size, status="completed")
def _empty_message(entries: list[dict], stats: dict) -> str:
    return "" if entries else ("No library items match the current search or filters." if stats["totalDownloads"] else "Your completed downloads and local files will appear here.")
def _matches(entry: dict, query: str, media: str | None, status: str | None, cache: dict[str, dict]) -> bool:
    fp, ana = str(entry.get("filePath") or ""), cache.get(str(entry.get("filePath") or ""), {})
    haystack = f"{entry.get('title', '')} {fp} {entry.get('url', '')} {ana.get('key', '')} {ana.get('enharmonic', '')} {ana.get('camelot', '')} {ana.get('bpm', '')}".casefold()
    return (not query or query in haystack) and (not media or entry.get("mediaType") == media) and (not status or entry.get("status") == status)
def _summary_text(stats: dict) -> str:
    t = stats["totalDownloads"]
    return f"{t} records · {stats['successful']} completed · {stats['failed']} failed · {stats['totalSizeMb']:.1f} MB" if t else "No downloads recorded yet."
