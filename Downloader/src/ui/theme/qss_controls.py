"""Buttons and input QSS with strict 4-tier hierarchy."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    fg = tokens.get("accent_text", "#061815")
    return f"""
    QPushButton {{ min-height: 32px; padding: 0 12px; border-radius: 6px; font-weight: 600; font-size: 9pt; }}
    QPushButton#PrimaryButton {{ background: {accent}; color: {fg}; border: 1px solid {accent}; font-weight: 700; }}
    QPushButton#PrimaryButton:hover {{ background: {accent}; border-color: {tokens['text']}; }}
    QPushButton#PrimaryButton:pressed {{ background: {accent}; border-color: {tokens['text']}; }}
    QPushButton#PrimaryButton:disabled {{ background: {tokens['panel']}; color: {tokens['text_subtle']}; border-color: {tokens['border']}; }}
    QPushButton#SecondaryButton {{ background: {tokens['surface']}; color: {tokens['text']}; border: 1px solid {tokens['border_strong']}; }}
    QPushButton#SecondaryButton:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['text_muted']}; }}
    QPushButton#SecondaryButton:pressed {{ background: {tokens['panel']}; }}
    QPushButton#SecondaryButton:disabled {{ background: {tokens['panel']}; color: {tokens['text_subtle']}; border-color: {tokens['border']}; }}
    QPushButton#ToolButton {{ min-height: 28px; padding: 0 9px; background: {tokens['panel']}; color: {tokens['text_muted']}; border: 1px solid {tokens['border']}; border-radius: 5px; font-weight: 600; font-size: 8.5pt; }}
    QPushButton#ToolButton:hover {{ background: {tokens['surface_hover']}; color: {tokens['text']}; border-color: {tokens['border_strong']}; }}
    QPushButton#ToolButton:pressed {{ background: {tokens['surface']}; }}
    QPushButton#ToolButton:checked {{ background: {tokens.get('accent_surface', '#112926')}; color: {accent}; border-color: {accent}; }}
    QPushButton#ToolButton:disabled {{ background: transparent; color: {tokens['text_subtle']}; border-color: {tokens['border']}; }}
    QPushButton#DangerButton {{ background: transparent; color: {tokens['danger']}; border: 1px solid {tokens['border_strong']}; }}
    QPushButton#DangerButton:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['danger']}; }}
    QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {accent}; outline: none; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ min-height: 32px; padding: 0 10px; background: {tokens['bg']}; color: {tokens['text']}; border: 1px solid {tokens['border']}; border-radius: 6px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {tokens['border_strong']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {tokens['panel']}; color: {tokens['text']}; border: 1px solid {tokens['border_strong']}; selection-background-color: {accent}; selection-color: {fg}; border-radius: 6px; }}
    QCheckBox {{ spacing: 8px; color: {tokens['text']}; min-height: 24px; }}
    QPushButton#StateToggle {{ min-height: 28px; padding: 0 10px; background: {tokens['bg']}; color: {tokens['text_subtle']}; border: 1px solid {tokens['border']}; border-radius: 5px; font-weight: 700; font-size: 8.5pt; }}
    QPushButton#StateToggle:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['border_strong']}; }}
    QPushButton#StateToggle:checked {{ background: {accent}; color: {fg}; border-color: {accent}; }}
    QProgressBar {{ min-height: 5px; max-height: 5px; border: none; border-radius: 2px; background: {tokens['border']}; color: transparent; }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}
    """
