"""Build the dense download workspace with unified command deck and queue table."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from src.ui.components.controls import SmoothScrollArea
from src.ui.components.download_options import DownloadOptions
from src.ui.components.empty_state import EmptyState
from src.ui.components.health_banner import HealthBanner
from src.ui.components.input_bar import InputBar
from src.ui.i18n import tr


def build(workspace) -> None:
    outer = QVBoxLayout(workspace)
    outer.setContentsMargins(0, 0, 0, 0)
    workspace.pageScroll = SmoothScrollArea()
    workspace.pageScroll.setWidgetResizable(True)
    workspace.pageContent = QWidget()
    root = QVBoxLayout(workspace.pageContent)
    root.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    root.setContentsMargins(20, 16, 20, 16)
    root.setSpacing(10)
    root.addLayout(_header(workspace))
    _add_primary_controls(workspace, root)
    _add_queue_regions(workspace, root)
    root.addStretch(1)
    workspace.queueContainer.hide()
    workspace.pageScroll.setWidget(workspace.pageContent)
    outer.addWidget(workspace.pageScroll)


def _add_primary_controls(workspace, root: QVBoxLayout) -> None:
    workspace.healthBanner = HealthBanner(workspace._cfg.get("downloadPath"))
    root.addWidget(workspace.healthBanner)
    workspace.inputBar = InputBar()
    workspace.inputBar.urlAdded.connect(workspace.addUrl)
    workspace.inputBar.urlsImported.connect(workspace.addUrls)
    root.addWidget(workspace.inputBar)
    workspace.downloadOptions = DownloadOptions(workspace._cfg)
    workspace.downloadOptions.presetChanged.connect(workspace._applyPresetToQueued)
    workspace.downloadOptions.engineChanged.connect(workspace._applyEngineToQueued)
    workspace.downloadOptions.pathChanged.connect(workspace.healthBanner.setDownloadPath)
    workspace.downloadOptions.downloadAllRequested.connect(workspace._onDownloadAll)
    root.addWidget(workspace.downloadOptions)


def _add_queue_regions(workspace, root: QVBoxLayout) -> None:
    workspace.bannerArea = QVBoxLayout()
    workspace.bannerArea.setSpacing(6)
    root.addLayout(workspace.bannerArea)
    workspace.queueContainer = QWidget()
    workspace.listLay = QVBoxLayout(workspace.queueContainer)
    workspace.listLay.setContentsMargins(0, 0, 0, 0)
    workspace.listLay.setSpacing(6)
    workspace.listLay.addWidget(_table_header(workspace))
    workspace.listLay.addStretch(1)
    root.addWidget(workspace.queueContainer)
    workspace.emptyState = EmptyState(workspace._cfg)
    root.addWidget(workspace.emptyState)


def _table_header(workspace) -> QFrame:
    bar = QFrame(objectName="TableHeaderBar")
    row = QHBoxLayout(bar)
    row.setContentsMargins(10, 5, 10, 5)
    row.setSpacing(12)
    workspace.colMedia = QLabel("MEDIA / SOURCE", objectName="TableHeader")
    workspace.colFormat = QLabel("OUTPUT", objectName="TableHeader")
    workspace.colFormat.setFixedWidth(156)
    workspace.colStatus = QLabel("STATE / PROGRESS", objectName="TableHeader")
    workspace.colAction = QLabel("ACTION", objectName="TableHeader")
    row.addWidget(workspace.colMedia, 4)
    row.addWidget(workspace.colFormat)
    row.addWidget(workspace.colStatus, 3)
    row.addWidget(workspace.colAction)
    return bar


def _header(workspace) -> QHBoxLayout:
    row = QHBoxLayout()
    labels = QVBoxLayout()
    labels.setSpacing(2)
    workspace.titleLabel = QLabel("Downloads", objectName="PageTitle")
    workspace.subtitleLabel = QLabel(
        "Paste a link, verify output format and folder, then start the queue.",
        objectName="PageSubtitle",
    )
    workspace.subtitleLabel.setWordWrap(True)
    labels.addWidget(workspace.titleLabel)
    labels.addWidget(workspace.subtitleLabel)
    workspace.queueCount = QLabel("0 items", objectName="NeutralBadge")
    row.addLayout(labels, 1)
    row.addWidget(workspace.queueCount)
    return row


def set_language(workspace, lang: str) -> None:
    workspace.titleLabel.setText(tr("dl.title", lang))
    workspace.subtitleLabel.setText(tr("dl.subtitle", lang))
    workspace.colMedia.setText(tr("dl.col_media", lang))
    workspace.colFormat.setText(tr("dl.col_format", lang))
    workspace.colStatus.setText(tr("dl.col_status", lang))
    workspace.colAction.setText(tr("dl.col_action", lang))
    workspace.inputBar.setLanguage(lang)
    workspace.downloadOptions.setLanguage(lang)
