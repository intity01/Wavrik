"""Layout construction and filter helpers for LibraryInterface."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, DangerPushButton, LineEdit, PushButton, SmoothScrollArea
from src.ui.i18n import tr

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}


def build_library_ui(page) -> None:
    root = QVBoxLayout(page)
    root.setContentsMargins(20, 16, 20, 16)
    root.setSpacing(10)
    page.summary = QLabel(objectName="NeutralBadge")
    header, labels = QHBoxLayout(), QVBoxLayout()
    page.titleLabel = QLabel("Library", objectName="PageTitle")
    page.subtitleLabel = QLabel(tr("lib.subtitle", "en"), objectName="PageSubtitle")
    labels.addWidget(page.titleLabel)
    labels.addWidget(page.subtitleLabel)
    page.addLocalBtn, page.clearBtn = PushButton("Add local file"), DangerPushButton("Clear library")
    page.addLocalBtn.clicked.connect(page._add_local)
    page.clearBtn.clicked.connect(page._clear)
    header.addLayout(labels, 1)
    for w in (page.summary, page.addLocalBtn, page.clearBtn):
        header.addWidget(w)
    filters = QHBoxLayout()
    page.searchBar = LineEdit(placeholderText=tr("lib.search_placeholder", "en"))
    page.typeFilter, page.statusFilter = ComboBox(), ComboBox()
    page.typeFilter.addItems(["All media", "Audio", "Video"])
    page.statusFilter.addItems(["All statuses", "Completed", "Failed", "Cancelled"])
    page.searchBar.textChanged.connect(page._debounce.start)
    page.typeFilter.currentIndexChanged.connect(page._apply_search)
    page.statusFilter.currentIndexChanged.connect(page._apply_search)
    for w, st in ((page.searchBar, 1), (page.typeFilter, 0), (page.statusFilter, 0)):
        filters.addWidget(w, st)
    _build_table_and_scroll(page, root, header, filters)


def _build_table_and_scroll(page, root: QVBoxLayout, header: QHBoxLayout, filters: QHBoxLayout) -> None:
    page.tableHeader = QFrame(objectName="TableHeaderBar")
    t_row = QHBoxLayout(page.tableHeader)
    t_row.setContentsMargins(12, 5, 12, 5)
    page.colTrack = QLabel("TITLE / FORMAT", objectName="TableHeader")
    page.colHarmony = QLabel("KEY · CAMELOT · BPM", objectName="TableHeader")
    page.colHarmony.setFixedWidth(186)
    page.colStatus = QLabel("STATUS", objectName="TableHeader")
    page.colActions = QLabel("ACTIONS", objectName="TableHeader")
    for w, st in ((page.colTrack, 4), (page.colHarmony, 0), (page.colStatus, 2), (page.colActions, 0)):
        t_row.addWidget(w, st)
    page.scrollArea, page.scrollContent = SmoothScrollArea(widgetResizable=True), QWidget()
    page.listLay = QVBoxLayout(page.scrollContent)
    page.listLay.setContentsMargins(0, 0, 0, 0)
    page.listLay.setSpacing(6)
    page.listLay.addStretch(1)
    page.scrollArea.setWidget(page.scrollContent)
    page.loadMoreBtn, page.emptyLabel = PushButton("Load more"), QLabel(objectName="MutedText")
    page.loadMoreBtn.hide()
    page.loadMoreBtn.clicked.connect(page._load_more)
    root.addLayout(header)
    root.addLayout(filters)
    for w, st in ((page.tableHeader, 0), (page.scrollArea, 1), (page.loadMoreBtn, 0), (page.emptyLabel, 0)):
        root.addWidget(w, st)


def record_local_file(history_manager, path: Path) -> None:
    media = "video" if path.suffix.lower() in VIDEO_EXTS else "audio"
    fmt = path.suffix.lstrip(".").upper() or "FILE"
    history_manager.addEntry("", path.stem, media, fmt, str(path), True, path.stat().st_size, status="completed")


def empty_message(entries: list[dict], stats: dict) -> str:
    if entries:
        return ""
    if stats["totalDownloads"]:
        return "No library items match the current search or filters."
    return "Your completed downloads and local files will appear here."


def matches_entry(entry: dict, query: str, media: str | None, status: str | None, cache: dict[str, dict]) -> bool:
    fp = str(entry.get("filePath") or "")
    ana = cache.get(fp, {})
    haystack = f"{entry.get('title', '')} {fp} {entry.get('url', '')} {ana.get('key', '')} {ana.get('enharmonic', '')} {ana.get('camelot', '')} {ana.get('bpm', '')}".casefold()
    return (not query or query in haystack) and (not media or entry.get("mediaType") == media) and (not status or entry.get("status") == status)


def summary_text(stats: dict) -> str:
    t = stats["totalDownloads"]
    return f"{t} records · {stats['successful']} completed · {stats['failed']} failed · {stats['totalSizeMb']:.1f} MB" if t else "No downloads recorded yet."
