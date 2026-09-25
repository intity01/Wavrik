"""Navigation and component QSS for macOS."""

COMPONENT_QSS = """
QWidget#NavigationPanel {{
    background: rgba(255, 255, 255, 0.02);
    border-right: 1px solid rgba(120, 120, 120, 0.15);
}}
QWidget#NavigationPanel[macosSidebar="true"] {{ background: rgba(255, 255, 255, 0.01); }}
QPushButton#NavigationButton {{
    border-radius: 6px;
    min-height: 42px;
    padding-left: 14px;
}}
QPushButton#NavigationButton:checked {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(120, 120, 120, 0.2);
}}
QFrame#Card, QFrame#QueueCard, QFrame#HistoryCard, QFrame#SettingsCard {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(120, 120, 120, 0.15);
    border-radius: 8px;
}}
QFrame#Card:hover, QFrame#QueueCard:hover, QFrame#HistoryCard:hover {{
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(120, 120, 120, 0.25);
}}
QProgressBar {{
    min-height: 4px;
    max-height: 4px;
    border: none;
    border-radius: 2px;
    background: rgba(120, 120, 120, 0.2);
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}
QToolTip {{
    background: rgba(30, 30, 30, 0.95);
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(120, 120, 120, 0.4);
    background: rgba(255, 255, 255, 0.05);
}}
QCheckBox::indicator:hover {{ border-color: rgba(120, 120, 120, 0.6); }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: rgba(30, 30, 30, 0.98);
    border: 1px solid rgba(120, 120, 120, 0.3);
    border-radius: 8px;
    selection-background-color: {accent};
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 32px;
    padding: 4px 8px;
    border-radius: 4px;
}}
"""
