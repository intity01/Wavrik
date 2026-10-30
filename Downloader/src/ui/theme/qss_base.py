"""Root and typography QSS for Precision Pro-Utility."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    accent_bg = tokens.get("accent_surface", "#112926")
    accent_bd = tokens.get("accent_border", "#1F4F48")
    return f"""
    QMainWindow, QWidget#AppRoot, QStackedWidget {{ background: {tokens['bg']}; color: {tokens['text']}; }}
    QWidget {{ color: {tokens['text']}; font-family: "Inter", "Segoe UI", ".SF Pro Text"; font-size: 9.5pt; }}
    QLabel#BrandTitle {{ font-size: 12pt; font-weight: 800; color: {tokens['text']}; }}
    QLabel#BrandSubtitle {{ font-size: 8pt; color: {tokens['text_subtle']}; }}
    QLabel#NavCategoryLabel {{ font-size: 7.5pt; font-weight: 700; color: {tokens['text_subtle']}; padding-left: 10px; padding-top: 10px; padding-bottom: 2px; letter-spacing: 0.6px; }}
    QLabel#PageTitle {{ font-size: 15pt; font-weight: 700; color: {tokens['text']}; letter-spacing: -0.3px; }}
    QLabel#PageSubtitle, QLabel#MutedText {{ color: {tokens['text_muted']}; font-size: 9pt; }}
    QLabel#TableHeader {{ font-size: 8pt; font-weight: 700; color: {tokens['text_subtle']}; letter-spacing: 0.5px; }}
    QLabel#SectionTitle {{ font-size: 10pt; font-weight: 600; color: {tokens['text']}; }}
    QLabel#SectionDesc {{ font-size: 8.5pt; color: {tokens['text_muted']}; }}
    QLabel#MonoValue {{ font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace; font-size: 9pt; font-weight: 600; color: {tokens['text']}; }}
    QLabel#CategoryPill, QLabel#StepBadge {{ font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace; font-size: 8.5pt; font-weight: 700; color: {accent}; background: {accent_bg}; border: 1px solid {accent_bd}; border-radius: 4px; padding: 2px 7px; }}
    QLabel#NeutralBadge {{ font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace; font-size: 8pt; font-weight: 600; color: {tokens['text_muted']}; background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 4px; padding: 2px 6px; }}
    QLabel#ExperimentalBadge {{ color: {tokens['warning']}; background: {tokens['panel']}; border: 1px solid {tokens['border']}; border-radius: 4px; padding: 2px 6px; font-size: 8pt; font-weight: 600; }}
    QLabel#InlineError {{ color: {tokens['danger']}; font-size: 8.5pt; font-weight: 600; }}
    QLabel#SuccessText {{ color: {tokens['success']}; }}
    QLabel#WarningText {{ color: {tokens['warning']}; }}
    QLabel#DangerText {{ color: {tokens['danger']}; }}
    QToolTip {{ background: {tokens['surface']}; color: {tokens['text']}; border: 1px solid {tokens['border_strong']}; padding: 5px 8px; border-radius: 5px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {tokens['border_strong']}; min-height: 28px; border-radius: 3px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
