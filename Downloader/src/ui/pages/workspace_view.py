"""Build the vertically responsive download workspace with clear categorized structure."""

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
    root.setContentsMargins(24, 20, 24, 20)
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
    q_top = QHBoxLayout()
    q_top.addWidget(QLabel("STEP 3 · QUEUE", objectName="CategoryPill"))
    q_top.addWidget(QLabel("3. รายการดาวน์โหลด (Active Queue)", objectName="SectionTitle"), 1)
    root.addLayout(q_top)
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
    labels.setSpacing(2)
    labels.addWidget(QLabel("Downloads · ระบบดาวน์โหลดและนำเข้าสื่อ", objectName="PageTitle"))
    subtitle = QLabel("ทำงาน 3 ขั้นตอน: (1) วางลิงก์ -> (2) เลือกประเภท Audio/Video และคุณภาพ -> (3) จัดการคิวงาน (ไฟล์เสียงจะถูกวิเคราะห์คีย์และ BPM อัตโนมัติ)", objectName="PageSubtitle")
    subtitle.setWordWrap(True)
    labels.addWidget(subtitle)
    workspace.queueCount = QLabel("0 items", objectName="MutedText")
    row.addLayout(labels, 1)
    row.addWidget(workspace.queueCount)
    return row
