"""Navigation, toolbars, compact rows, and status QSS."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    return f"""
    QWidget#NavigationPanel {{ background: {tokens['panel']}; border-right: 1px solid {tokens['border']}; }}
    QFrame#BrandHeader {{ background: transparent; border: none; border-bottom: 1px solid {tokens['border']}; border-radius: 0px; }}
    QFrame#SubSectionBox {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 6px; }}
    QPushButton#NavigationButton {{ min-height: 34px; text-align: left; padding-left: 12px; background: transparent; color: {tokens['text_muted']}; border: 1px solid transparent; border-radius: 6px; font-weight: 600; font-size: 9pt; }}
    QPushButton#NavigationButton:hover {{ background: {tokens['surface']}; color: {tokens['text']}; }}
    QPushButton#NavigationButton:checked {{ background: {tokens['surface']}; color: {tokens['text']}; border: 1px solid {tokens['border_strong']}; }}
    QFrame#CommandDeck, QFrame#InputPanel, QFrame#DownloadOptions {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 6px; }}
    QFrame#TableHeaderBar {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 5px; }}
    QFrame#Card, QFrame#QueueCard, QFrame#HistoryCard, QFrame#LibraryCard {{ background: {tokens['surface']}; border: 1px solid {tokens['border']}; border-radius: 6px; }}
    QFrame#Card:hover, QFrame#QueueCard:hover, QFrame#HistoryCard:hover, QFrame#LibraryCard:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['border_strong']}; }}
    QFrame#AudioToolsCard, QFrame#SettingsCard {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 6px; }}
    QLabel#FieldLabel {{ color: {tokens['text_subtle']}; font-size: 8pt; font-weight: 700; letter-spacing: 0.3px; }}
    QLabel#PresetLabel {{ font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace; color: {tokens['text_muted']}; font-size: 8.5pt; font-weight: 600; }}
    QLabel#Thumbnail {{ background: {tokens['bg']}; color: {tokens['text_subtle']}; border: 1px solid {tokens['border']}; border-radius: 4px; font-size: 7.5pt; }}
    QFrame#InfoBanner {{ background: {tokens['surface']}; border: 1px solid {tokens['border_strong']}; border-radius: 6px; }}
    QFrame#HealthGood {{ background: {tokens['panel']}; border: 1px solid {tokens['success']}; border-radius: 6px; }}
    QFrame#HealthWarning {{ background: {tokens['panel']}; border: 1px solid {tokens['warning']}; border-radius: 6px; }}
    QLabel[status="ready"], QLabel[status="queued"], QLabel[status="fetching"] {{ color: {tokens['text_muted']}; font-size: 8.5pt; }}
    QLabel[status="downloading"], QLabel[status="processing"] {{ color: {accent}; font-weight: 600; font-size: 8.5pt; }}
    QLabel[status="completed"] {{ color: {tokens['success']}; font-weight: 600; font-size: 8.5pt; }}
    QLabel[status="failed"] {{ color: {tokens['danger']}; font-weight: 600; font-size: 8.5pt; }}
    QLabel[status="cancelled"] {{ color: {tokens['text_subtle']}; font-size: 8.5pt; }}
    """
