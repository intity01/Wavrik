"""Root and typography QSS."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    return f"""
    QMainWindow, QWidget#AppRoot, QStackedWidget {{ background: {tokens['bg']}; color: {tokens['text']}; }}
    QWidget {{ color: {tokens['text']}; font-family: "Inter", "Segoe UI", ".SF Pro Text"; font-size: 10pt; }}
    QLabel#PageTitle {{ font-size: 20pt; font-weight: 700; color: {tokens['text']}; letter-spacing: -0.5px; }}
    QLabel#PageSubtitle, QLabel#MutedText {{ color: {tokens['text_muted']}; }}
    QLabel#SectionTitle {{ font-size: 11pt; font-weight: 700; color: {tokens['text']}; letter-spacing: -0.3px; }}
    QLabel#InlineError {{ color: {tokens['danger']}; font-size: 9pt; }}
    QLabel#SuccessText {{ color: {tokens['success']}; }}
    QLabel#WarningText {{ color: {tokens['warning']}; }}
    QLabel#DangerText {{ color: {tokens['danger']}; }}
    QToolTip {{ background: {tokens['surface']}; color: {tokens['text']}; border: 1px solid {tokens['border']}; padding: 6px; border-radius: 6px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {tokens['border_strong']}; min-height: 28px; border-radius: 4px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
