"""Searchable download history."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import (
    ComboBox,
    DangerPushButton,
    LineEdit,
    MessageBox,
    PushButton,
    SmoothScrollArea,
)
from src.ui.components.history_card import HistoryCard


class HistoryInterface(QWidget):
    redownloadRequested = pyqtSignal(str)

    def __init__(self, historyManager, parent=None):
        super().__init__(parent)
        self._hist = historyManager
        self._limit = 50
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._apply_search)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        root.addLayout(self._build_header())
        root.addLayout(self._build_filters())
        self.summary = QLabel()
        self.summary.setObjectName("MutedText")
        root.addWidget(self.summary)
        self._build_list(root)
        self.refresh()

    def _build_header(self) -> QHBoxLayout:
        header, labels = QHBoxLayout(), QVBoxLayout()
        title, subtitle = QLabel("History"), QLabel("Find completed files, retry failures, or open their folders.")
        title.setObjectName("PageTitle")
        subtitle.setObjectName("PageSubtitle")
        labels.addWidget(title)
        labels.addWidget(subtitle)
        clear = DangerPushButton("Clear history")
        clear.setAccessibleDescription("Remove all saved history records without deleting downloaded files")
        clear.clicked.connect(self._clear)
        header.addLayout(labels, 1)
        header.addWidget(clear)
        return header

    def _build_filters(self) -> QHBoxLayout:
        filters = QHBoxLayout()
        self.searchBar = LineEdit()
        self.searchBar.setPlaceholderText("Search title or URL")
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
        self.loadMoreBtn.setAccessibleDescription("Load more history records")
        self.loadMoreBtn.clicked.connect(self._load_more)
        self.loadMoreBtn.hide()
        self.emptyLabel = QLabel()
        self.emptyLabel.setObjectName("MutedText")
        root.addWidget(self.scrollArea, 1)
        root.addWidget(self.loadMoreBtn)
        root.addWidget(self.emptyLabel)

    def _apply_search(self) -> None:
        self._limit = 50
        self.refresh()

    def _load_more(self) -> None:
        self._limit += 50
        self.refresh()

    def refresh(self, *_args) -> None:
        entries = self._filtered_entries()
        visible = entries[:self._limit]
        self._clear_cards()
        for entry in visible:
            card = HistoryCard(entry)
            card.redownloadRequested.connect(self.redownloadRequested.emit)
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
        msg = "This removes history records only. Downloaded files will not be deleted."
        if MessageBox("Clear history", msg, self, "Clear history").exec():
            self._hist.clearHistory()
            self._limit = 50
            self.refresh()


def _empty_message(entries: list[dict], stats: dict) -> str:
    if entries:
        return ""
    if stats["totalDownloads"]:
        return "No history matches the current search or filters."
    return "Your completed and failed downloads will appear here."


def _matches(entry: dict, query: str, media: str | None, status: str | None) -> bool:
    haystack = f"{entry.get('title', '')} {entry.get('url', '')}".casefold()
    return (not query or query in haystack) and (not media or entry.get("mediaType") == media) and (not status or entry.get("status") == status)


def _summary_text(stats: dict) -> str:
    total = stats["totalDownloads"]
    if not total:
        return "No downloads recorded yet."
    return f"{total} records · {stats['successful']} completed · {stats['failed']} failed · {stats['totalSizeMb']:.1f} MB"
