"""Comprehensive verification of UI/UX redesign per DESIGN.md."""

from __future__ import annotations

from unittest.mock import MagicMock

from PyQt6.QtCore import Qt

from src.core.updater import UpdateManager
from src.ui.components.controls import PrimaryPushButton, PushButton, ToolButton
from src.ui.i18n import STRINGS_EN, STRINGS_TH
from src.ui.main_window import MediaDownloaderUI
from src.ui.theme.tokens import DARK, LIGHT


def _make_window(qtbot, config, logger, fake_downloader, history):
    tray = MagicMock(isAvailable=lambda: False)
    win = MediaDownloaderUI(config, logger, fake_downloader, UpdateManager("2.0.0", "o/r", logger), tray, history)
    qtbot.addWidget(win)
    win.show()
    return win


def test_button_tiers_and_hierarchy(qtbot, config, logger, fake_downloader, history):
    win = _make_window(qtbot, config, logger, fake_downloader, history)
    ws_primary = [b for b in win.pageWorkspace.findChildren(PrimaryPushButton) if b.isVisibleTo(win.pageWorkspace)]
    assert len(ws_primary) == 1 and ws_primary[0] is win.pageWorkspace.inputBar.addButton
    assert isinstance(win.pageWorkspace.downloadOptions.downloadAllButton, PushButton)
    at_primary = [b for b in win.pageAudioTools.findChildren(PrimaryPushButton) if b.isVisibleTo(win.pageAudioTools)]
    assert len(at_primary) == 1 and at_primary[0] is win.pageAudioTools.exportBtn
    assert isinstance(win.pageAudioTools.batchBtn, PushButton)
    assert isinstance(win.pageAudioTools.previewShiftedBtn, PushButton)
    assert isinstance(win.pageAudioTools.openFolderBtn, ToolButton)
    assert LIGHT["danger"] == "#F85149" and DARK["danger"] == "#F85149"


def test_dimensions_fonts_and_margins(qtbot, config, logger, fake_downloader, history):
    win = _make_window(qtbot, config, logger, fake_downloader, history)
    assert win.navigationPanel.maximumWidth() == 176 and win.navigationPanel.minimumWidth() == 176
    content_layouts = [
        win.pageWorkspace.pageContent.layout(),
        win.pageLibrary.layout(),
        win.pageSettings.layout().itemAt(0).widget().widget().layout(),
        win.pageAudioTools.layout().itemAt(0).widget().widget().layout(),
    ]
    for lay in content_layouts:
        m = lay.contentsMargins()
        assert (m.left(), m.top(), m.right(), m.bottom()) == (24, 24, 24, 24)
        assert lay.spacing() == 14
    from src.ui.theme import qss_base, qss_controls
    cq, bq = qss_controls.build(LIGHT, LIGHT["accent"]), qss_base.build(LIGHT, LIGHT["accent"])
    assert "min-height: 38px" in cq and "min-height: 32px" in cq
    assert "font-size: 20pt" in bq and "font-weight: 700" in bq and "font-size: 11pt" in bq


def test_download_options_layout_and_keyboard(qtbot, config, logger, fake_downloader, history):
    win = _make_window(qtbot, config, logger, fake_downloader, history)
    opt = win.pageWorkspace.downloadOptions
    assert opt.pathInput.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert opt.layout().count() >= 3

    # Tab order verification on AudioTools
    at = win.pageAudioTools
    assert at.chooseFileBtn.nextInFocusChain() is not None
    assert at.stemModeCombo.nextInFocusChain() is not None


def test_library_cache_bounded_lru(history, config):
    from src.ui.pages.library_page import LibraryInterface
    lib = LibraryInterface(history, config)
    for i in range(250):
        lib.storeAnalysisResult({"filePath": f"file_{i}.mp3", "key": "C major", "bpm": 120.0})
    assert len(lib._analysisCache) <= 200
    assert "file_249.mp3" in lib._analysisCache and "file_0.mp3" not in lib._analysisCache


def test_thai_translation_catalog_completeness():
    missing = set(STRINGS_EN.keys()) - set(STRINGS_TH.keys())
    assert not missing, f"Missing Thai translation keys: {missing}"
    for k, v in STRINGS_TH.items():
        assert v.strip(), f"Empty Thai translation for key {k}"


def test_cascading_language_switch(qtbot, config, logger, fake_downloader, history):
    win = _make_window(qtbot, config, logger, fake_downloader, history)
    win._apply_language("th")
    assert win.pageWorkspace.titleLabel.text() == "ดาวน์โหลดสื่อ"
    assert win.pageLibrary.titleLabel.text() == "คลังสื่อและผลวิเคราะห์"
    assert win.pageAudioTools.titleLabel.text() == "สตูดิโอวิเคราะห์และปรับแต่งเสียง"
    assert win.pageSettings.titleLabel.text() == "ตั้งค่าระบบ"
    assert win.pageWorkspace.inputBar.addButton.text() == "เพิ่มลงคิว"
    assert win.pageWorkspace.downloadOptions.browseButton.text() == "เปลี่ยนโฟลเดอร์"
    assert win.pageWorkspace.downloadOptions.advancedButton.text() == "ตัวเลือกเพิ่มเติม"
    assert win.pageWorkspace.downloadOptions.downloadAllButton.text() == "ดาวน์โหลดทั้งหมด"
    assert win.pageAudioTools.exportBtn.text() == "ส่งออกไฟล์ผลลัพธ์"
    assert win.pageAudioTools.chooseFileBtn.text() == "เลือกไฟล์เสียง"
    assert win.pageAudioTools.outputPreviewLabel.text() == "ไฟล์ต้นฉบับจะไม่ถูกเขียนทับเด็ดขาด"
    assert win.pageAudioTools.statusLabel.text() == "เลือกไฟล์เสียงเพื่อเริ่มต้นใช้งาน"
    assert win.pageAudioTools.badgeLabel.text() == "ผลประมาณการ"

    # Test QueueItemCard localization
    win.pageWorkspace.addUrl("https://youtube.com/watch?v=12345678901")
    card = list(win.pageWorkspace._cards.values())[0]
    assert card._title.text() == "กำลังอ่านข้อมูลสื่อ"
    assert card._lblStatus.text() == "กำลังอ่านข้อมูลสื่อ"
    assert card._lblMeta.text() == "กำลังรอข้อมูลสื่อ"
    assert card._btnDl.text() == "ดาวน์โหลด"
    assert card._btnDel.text() == "ลบออก"
    assert win.pageWorkspace.downloadOptions.downloadAllButton.text() == "ดาวน์โหลดทั้งหมด (1)"

    # Switch back to English and verify full update
    win._apply_language("en")
    assert win.pageWorkspace.downloadOptions.downloadAllButton.text() == "Download all (1)"
    assert card._btnDl.text() == "Download"
    assert card._btnDel.text() == "Remove"
    assert card._title.text() == "Reading media information"
    assert card._lblStatus.text() == "Reading media information"
    assert card._lblMeta.text() == "Waiting for metadata"
    assert win.pageAudioTools.outputPreviewLabel.text() == "Original file is never overwritten."


def test_library_card_and_empty_state_localization(history, config):
    from src.ui.components.empty_state import EmptyState
    from src.ui.components.library_card import LibraryCard
    card = LibraryCard({"title": "Song", "status": "completed", "filePath": "a.mp3", "mediaType": "audio", "fileSize": 1048576})
    card.setLanguage("th")
    assert card.status.text() == "สำเร็จ"
    assert "ไฟล์เสียง" in card.metadata.text()
    card.setLanguage("en")
    assert card.status.text() == "Completed"
    assert "Audio" in card.metadata.text()

    # EmptyState first-run vs subsequent run
    config.set("firstRun", True)
    es = EmptyState(config)
    assert not any(c.isHidden() for c in es._cards)
    config.set("firstRun", False)
    es.setLanguage("th")
    assert all(c.isHidden() for c in es._cards)
    assert es.title.text() == "คิวดาวน์โหลดว่างเปล่า"
