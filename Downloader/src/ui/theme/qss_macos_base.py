"""Typography, controls, and scrollbars for macOS QSS."""

BASE_QSS = """
QWidget {{
    font-family: ".SF Pro Text", "SF Pro Text", "Inter", "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
QLabel#PageTitle {{
    font-family: ".SF Pro Display", ".SF Pro Text", "Inter", sans-serif;
    font-weight: 600;
    letter-spacing: -0.02em;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: rgba(120, 120, 120, 0.5);
    min-height: 28px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(120, 120, 120, 0.8); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(120, 120, 120, 0.5);
    min-width: 28px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: rgba(120, 120, 120, 0.8); }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QPushButton {{
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}}
QPushButton#PrimaryButton {{
    background: {accent};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
}}
QPushButton#PrimaryButton:hover {{ background: {accent}; opacity: 0.9; }}
QPushButton#PrimaryButton:pressed {{ background: {accent}; opacity: 0.8; }}
QPushButton#SecondaryButton {{
    background: rgba(120, 120, 120, 0.1);
    color: {text};
    border: 1px solid rgba(120, 120, 120, 0.2);
    border-radius: 6px;
}}
QPushButton#SecondaryButton:hover {{
    background: rgba(120, 120, 120, 0.15);
    border-color: rgba(120, 120, 120, 0.3);
}}
QLineEdit, QComboBox, QSpinBox {{
    border-radius: 6px;
    border: 1px solid rgba(120, 120, 120, 0.3);
    background: rgba(255, 255, 255, 0.05);
    selection-background-color: {accent};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {accent};
    background: rgba(255, 255, 255, 0.08);
}}
"""
