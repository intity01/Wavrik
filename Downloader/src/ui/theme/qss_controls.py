"""Buttons and input QSS."""

from __future__ import annotations


def build(tokens: dict[str, str], accent: str) -> str:
    fg = tokens.get("accent_text", "#081C19")
    return f"""
    QPushButton {{ min-height: 38px; padding: 0 14px; border-radius: 8px; font-weight: 600; }}
    QPushButton#PrimaryButton {{ background: {accent}; color: {fg}; border: 1px solid {accent}; }}
    QPushButton#PrimaryButton:hover {{ background: {accent}; border-color: {tokens['text']}; }}
    QPushButton#PrimaryButton:pressed {{ background: {accent}; border-color: {tokens['text']}; }}
    QPushButton#PrimaryButton:disabled {{ background: {tokens['border']}; color: {tokens['text_subtle']}; border-color: {tokens['border']}; }}
    QPushButton#SecondaryButton, QPushButton#ToolButton {{ background: {tokens['surface']}; color: {tokens['text']}; border: 1px solid {tokens['border']}; }}
    QPushButton#SecondaryButton:hover, QPushButton#ToolButton:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['border_strong']}; }}
    QPushButton#SecondaryButton:pressed, QPushButton#ToolButton:pressed {{ background: {tokens['surface']}; }}
    QPushButton#SecondaryButton:disabled, QPushButton#ToolButton:disabled {{ background: {tokens['panel']}; color: {tokens['text_subtle']}; border-color: {tokens['border']}; }}
    QPushButton#DangerButton {{ background: transparent; color: {tokens['danger']}; border: 1px solid {tokens['danger']}; }}
    QPushButton#DangerButton:hover {{ background: {tokens['surface_hover']}; }}
    QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {accent}; outline: none; }}
    QLineEdit, QComboBox, QSpinBox {{ min-height: 38px; padding: 0 10px; background: {tokens['panel']}; color: {tokens['text']}; border: 1px solid {tokens['border']}; border-radius: 8px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {tokens['border_strong']}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{ background: {tokens['panel']}; color: {tokens['text']}; border: 1px solid {tokens['border']}; selection-background-color: {accent}; selection-color: {fg}; border-radius: 8px; }}
    QCheckBox {{ spacing: 8px; color: {tokens['text']}; min-height: 24px; }}
    QPushButton#StateToggle {{ min-height: 34px; padding: 0 10px; background: {tokens['panel']}; color: {tokens['text_subtle']}; border: 1px solid {tokens['border']}; border-radius: 8px; font-weight: 700; }}
    QPushButton#StateToggle:hover {{ background: {tokens['surface_hover']}; border-color: {tokens['border_strong']}; }}
    QPushButton#StateToggle:checked {{ background: {accent}; color: {fg}; border-color: {accent}; }}
    QProgressBar {{ min-height: 8px; max-height: 8px; border: none; border-radius: 4px; background: {tokens['border']}; color: transparent; }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
    """

