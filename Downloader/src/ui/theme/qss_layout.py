"""Navigation, cards, banners, and status QSS."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    return f"""
    QWidget#NavigationPanel {{ background: {tokens['panel']}; border-right: 1px solid {tokens['border']}; }}
    QFrame#BrandHeader {{ background: {tokens['surface']}; border: 1px solid {tokens['border']}; border-radius: 10px; }}
    QFrame#SubSectionBox {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 8px; }}
    QPushButton#NavigationButton {{ min-height: 42px; text-align: left; padding-left: 14px; background: transparent; color: {tokens['text_muted']}; border: none; border-radius: 8px; font-weight: 600; }}
    QPushButton#NavigationButton:hover {{ background: {tokens['surface_hover']}; color: {tokens['text']}; }}
    QPushButton#NavigationButton:checked {{ background: {tokens['surface']}; color: {accent}; border: 1px solid {tokens['border_strong']}; padding-left: 13px; }}
    QFrame#Card, QFrame#QueueCard, QFrame#HistoryCard, QFrame#LibraryCard, QFrame#AudioToolsCard, QFrame#SettingsCard {{ background: {tokens['surface']}; border: 1px solid {tokens['border']}; border-radius: 10px; }}
    QFrame#Card:hover, QFrame#QueueCard:hover, QFrame#HistoryCard:hover, QFrame#LibraryCard:hover, QFrame#AudioToolsCard:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['border_strong']}; }}
    QFrame#DownloadOptions {{ background: {tokens['surface']}; border: 1px solid {tokens['border']}; border-radius: 10px; }}
    QLabel#FieldLabel {{ color: {tokens['text_muted']}; font-size: 9pt; font-weight: 600; }}
    QLabel#PresetLabel {{ color: {tokens['text']}; font-weight: 600; }}
    QLabel#StepBadge {{ color: {accent}; font-weight: 700; background: #122B28; border: 1px solid #1E4E48; border-radius: 6px; padding: 3px 8px; }}
    QLabel#ExperimentalBadge {{ color: {tokens['warning']}; font-size: 9pt; font-weight: 600; }}
    QFrame#InputPanel {{ background: {tokens['surface']}; border: 1px solid {tokens['border_strong']}; border-radius: 10px; }}
    QLabel#Thumbnail {{ background: {tokens['panel']}; color: {tokens['text_muted']}; border: 1px solid {tokens['border']}; border-radius: 8px; }}
    QFrame#InfoBanner {{ background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 10px; }}
    QFrame#HealthGood {{ background: {tokens['surface']}; border: 1px solid {tokens['success']}; border-radius: 10px; }}
    QFrame#HealthWarning {{ background: {tokens['surface']}; border: 1px solid {tokens['warning']}; border-radius: 10px; }}
    QLabel[status="ready"], QLabel[status="queued"], QLabel[status="fetching"] {{ color: {tokens['text_muted']}; }}
    QLabel[status="downloading"], QLabel[status="processing"] {{ color: {accent}; font-weight: 600; }}
    QLabel[status="completed"] {{ color: {tokens['success']}; font-weight: 600; }}
    QLabel[status="failed"] {{ color: {tokens['danger']}; font-weight: 600; }}
    QLabel[status="cancelled"] {{ color: {tokens['text_subtle']}; }}
    """
