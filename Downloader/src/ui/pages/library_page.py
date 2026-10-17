"""Unified searchable media library (downloaded and local files)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, DangerPushButton, LineEdit, MessageBox, PushButton, SmoothScrollArea
from src.ui.components.library_card import LibraryCard
from src.ui.dialogs import get_open_file_path

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
_MEDIA_FILTER = "Media files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.webm);;All files (*.*)"


class LibraryInterface(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, historyManager, parent=None):
        super().__init__(parent)
        self._hist, self._limit = historyManager, 50
        self._debounce = QTimer(self, singleShot=True, interval=250)
        self._debounce.timeout.connect(self._apply_search)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        root.addLayout(self._build_header())
        root.addLayout(self._build_filters())
        self.summary = QLabel(objectName="MutedText")
        root.addWidget(self.summary)
        self._build_list(root)
        self.refresh()

    def _build_header(self) -> QHBoxLayout:
        header, labels = QHBoxLayout(), QVBoxLayout()
        title = QLabel("Library", objectName="PageTitle")
        subtitle = QLabel("Search downloaded tracks and local files, open folders, or send audio to Audio Tools.", objectName="PageSubtitle")
        labels.addWidget(title)
        labels.addWidget(subtitle)
        self.addLocalBtn = PushButton("Add local file")
        self.addLocalBtn.clicked.connect(self._add_local)
        clear = DangerPushButton("Clear library")
        clear.clicked.connect(self._clear)
        header.addLayout(labels, 1)
        header.addWidget(self.addLocalBtn)
        header.addWidget(clear)
        return header

    def _build_filters(self) -> QHBoxLayout:
        filters = QHBoxLayout()
        self.searchBar = LineEdit(placeholderText="Search title, file name, or URL")
        self.typeFilter, self.statusFilter = ComboBox(), ComboBox()
        self.typeFilter.addItems(["All media", "Audio", "Video"])
        self.statusFilter.addItems(["All statuses", "Completed", "Failed", "Cancelled"])
        self.searchBar.textChanged.connect(self._debounce.start)
        self.typeFilter.currentIndexChanged.connect(self._apply_search)
        self.statusFilter.currentIndexChanged.connect(self._apply_search)
        filters.addWidget(self.searchBar, 1)
        filters.addWidget(self.typeFilter)
        filters.addWidget(self.statusFilter)
        return filters

    def _build_list(self, root: QVBoxLayout) -> None:
        self.scrollArea, self.scrollContent = SmoothScrollArea(), QWidget()
        self.scrollArea.setWidgetResizable(True)
        self.listLay = QVBoxLayout(self.scrollContent)
        self.listLay.setContentsMargins(0, 0, 0, 0)
        self.listLay.setSpacing(10)
        self.listLay.addStretch(1)
        self.scrollArea.setWidget(self.scrollContent)
        self.loadMoreBtn = PushButton("Load more")
        self.loadMoreBtn.clicked.connect(self._load_more)
        self.loadMoreBtn.hide()
        self.emptyLabel = QLabel(objectName="MutedText")
        root.addWidget(self.scrollArea, 1)
        root.addWidget(self.loadMoreBtn)
        root.addWidget(self.emptyLabel)

    def _apply_search(self) -> None:
        self._limit = 50
        self.refresh()

    def _load_more(self) -> None:
        self._limit += 50
        self.refresh()

    def _add_local(self) -> None:
        selected = get_open_file_path(self, "Add local media file", _MEDIA_FILTER)
        if selected and selected.is_file():
            _record_local_file(self._hist, selected)
            self.refresh()

    def refresh(self, *_args) -> None:
        entries = self._filtered_entries()
        visible = entries[:self._limit]
        self._clear_cards()
        for entry in visible:
            card = LibraryCard(entry)
            card.redownloadRequested.connect(self.redownloadRequested.emit)
            card.openInAudioToolsRequested.connect(self.openInAudioToolsRequested.emit)
            self.listLay.insertWidget(self.listLay.count() - 1, card)
        stats = self._hist.getStats()
        self.summary.setText(_summary_text(stats))
        self.emptyLabel.setText(_empty_message(entries, stats))
        self.emptyLabel.setVisible(not entries)
        self.scrollArea.setVisible(bool(entries))
        self.loadMoreBtn.setVisible(len(entries) > len(visible))

    def _filtered_entries(self) -> list[dict]:
        query = self.searchBar.text().casefold().strip()
        media = {1: "audio", 2: "video"}.get(self.typeFilter.currentIndex())
        status = {1: "completed", 2: "failed", 3: "cancelled"}.get(self.statusFilter.currentIndex())
        return [e for e in self._hist.getHistory(1000) if _matches(e, query, media, status)]

    def _clear_cards(self) -> None:
        while self.listLay.count() > 1:
            item = self.listLay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear(self) -> None:
        msg = "This removes library records only. Media files on disk will not be deleted."
        if MessageBox("Clear library", msg, self, "Clear library").exec():
            self._hist.clearHistory()
            self._limit = 50
            self.refresh()


def _record_local_file(history_manager, path: Path) -> None:
    media = "video" if path.suffix.lower() in _VIDEO_EXTS else "audio"
    history_manager.addEntry("", path.stem, media, path.suffix.lstrip(".").upper() or "FILE", str(path), True, path.stat().st_size, status="completed")


def _empty_message(entries: list[dict], stats: dict) -> str:
    return "" if entries else ("No library items match the current search or filters." if stats["totalDownloads"] else "Your completed downloads and local files will appear here.")


def _matches(entry: dict, query: str, media: str | None, status: str | None) -> bool:
    haystack = f"{entry.get('title', '')} {entry.get('filePath', '')} {entry.get('url', '')}".casefold()
    return (not query or query in haystack) and (not media or entry.get("mediaType") == media) and (not status or entry.get("status") == status)


def _summary_text(stats: dict) -> str:
    t = stats["totalDownloads"]
    return f"{t} records · {stats['successful']} completed · {stats['failed']} failed · {stats['totalSizeMb']:.1f} MB" if t else "No downloads recorded yet."

