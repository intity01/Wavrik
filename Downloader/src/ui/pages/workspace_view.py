"""Build the vertically responsive download workspace."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from src.ui.components.controls import SmoothScrollArea
from src.ui.components.download_options import DownloadOptions
from src.ui.components.empty_state import EmptyState
from src.ui.components.health_banner import HealthBanner
from src.ui.components.input_bar import InputBar


def build(workspace) -> None:
    outer = QVBoxLayout(workspace)
    outer.setContentsMargins(0, 0, 0, 0)
    workspace.pageScroll = SmoothScrollArea()
    workspace.pageScroll.setWidgetResizable(True)
    workspace.pageContent = QWidget()
    root = QVBoxLayout(workspace.pageContent)
    root.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    root.setContentsMargins(24, 22, 24, 22)
    root.setSpacing(14)
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
    workspace.bannerArea.setSpacing(8)
    root.addLayout(workspace.bannerArea)
    workspace.queueContainer = QWidget()
    workspace.listLay = QVBoxLayout(workspace.queueContainer)
    workspace.listLay.setContentsMargins(0, 0, 0, 0)
    workspace.listLay.setSpacing(10)
    workspace.listLay.addStretch(1)
    root.addWidget(workspace.queueContainer)
    workspace.emptyState = EmptyState(workspace._cfg)
    root.addWidget(workspace.emptyState)


def _header(workspace) -> QHBoxLayout:
    row = QHBoxLayout()
    labels = QVBoxLayout()
    title = QLabel("Downloads")
    title.setObjectName("PageTitle")
    subtitle = QLabel("Add a link, choose the output once, then download the queue.")
    subtitle.setObjectName("PageSubtitle")
    subtitle.setWordWrap(True)
    labels.addWidget(title)
    labels.addWidget(subtitle)
    workspace.queueCount = QLabel("0 items")
    workspace.queueCount.setObjectName("MutedText")
    row.addLayout(labels, 1)
    row.addWidget(workspace.queueCount)
    return row
