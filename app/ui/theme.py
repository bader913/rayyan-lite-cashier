from __future__ import annotations


def normalize_theme_mode(value: str | None) -> str:
    mode = str(value or '').strip().lower()
    return mode if mode in {'light', 'dark'} else 'light'


def _palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)
    if mode == 'dark':
        return {
            'window_bg': '#0f172a',
            'text': '#e5eefc',
            'muted': '#94a3b8',
            'sidebar_bg': '#020817',
            'sidebar_border': '#1e293b',
            'sidebar_item': '#dbeafe',
            'sidebar_hover': '#16233b',
            'sidebar_selected': '#2563eb',
            'title': '#f8fafc',
            'section': '#e2e8f0',
            'card_bg': '#111c31',
            'card_border': '#22304d',
            'summary_bg': '#0b1324',
            'input_bg': '#0b1324',
            'input_border': '#334155',
            'input_focus': '#60a5fa',
            'table_alt': '#0b1324',
            'table_grid': '#22304d',
            'selection_bg': '#1d4ed8',
            'selection_fg': '#ffffff',
            'header_bg': '#16233b',
            'header_border': '#22304d',
            'header_fg': '#e2e8f0',
            'secondary_bg': '#22304d',
            'secondary_fg': '#e5eefc',
            'secondary_hover': '#334155',
            'shadow_line': '#1f2937',
        }
    return {
        'window_bg': '#eef2f7',
        'text': '#0f172a',
        'muted': '#64748b',
        'sidebar_bg': '#0f172a',
        'sidebar_border': '#1e293b',
        'sidebar_item': '#dbeafe',
        'sidebar_hover': '#1e293b',
        'sidebar_selected': '#2563eb',
        'title': '#0f172a',
        'section': '#1e293b',
        'card_bg': '#ffffff',
        'card_border': '#d8e1ef',
        'summary_bg': '#f8fafc',
        'input_bg': '#ffffff',
        'input_border': '#cbd5e1',
        'input_focus': '#2563eb',
        'table_alt': '#f8fafc',
        'table_grid': '#e2e8f0',
        'selection_bg': '#dbeafe',
        'selection_fg': '#0f172a',
        'header_bg': '#eef2ff',
        'header_border': '#dbe2ef',
        'header_fg': '#1e293b',
        'secondary_bg': '#e2e8f0',
        'secondary_fg': '#0f172a',
        'secondary_hover': '#cbd5e1',
        'shadow_line': '#e5e7eb',
    }


def build_app_stylesheet(theme_mode: str = 'light') -> str:
    p = _palette(theme_mode)
    return f"""
    QMainWindow, QWidget {{
      background: {p['window_bg']};
      color: {p['text']};
      font-family: 'Segoe UI', 'Tahoma', 'Arial';
      font-size: 13.5px;
    }}

    QToolTip {{
      background: {p['card_bg']};
      color: {p['text']};
      border: 1px solid {p['card_border']};
      padding: 6px;
    }}

    #sideFrame {{
      background: {p['sidebar_bg']};
      border-left: 1px solid {p['sidebar_border']};
    }}
    #appTitle {{ color: #ffffff; font-size: 26px; font-weight: 900; letter-spacing: .3px; }}
    #appSubtitle {{ color: #cbd5e1; font-size: 13px; }}
    #sidebar {{ background: transparent; border: none; color: {p['sidebar_item']}; outline: none; }}
    #sidebar::item {{
      padding: 14px 13px;
      margin: 4px 0;
      border-radius: 12px;
      color: {p['sidebar_item']};
    }}
    #sidebar::item:selected {{
      background: {p['sidebar_selected']};
      color: #ffffff;
      font-weight: 800;
    }}
    #sidebar::item:hover:!selected {{ background: {p['sidebar_hover']}; }}

    QLabel#pageTitle {{ font-size: 26px; font-weight: 900; color: {p['title']}; padding-bottom: 4px; }}
    QLabel#sectionTitle {{ font-size: 16px; font-weight: 800; color: {p['section']}; margin-top: 6px; }}
    QLabel#hintText {{ color: {p['muted']}; font-size: 12.5px; }}
    QLabel#cardTitle {{ color: {p['muted']}; font-size: 13px; font-weight: 700; }}
    QLabel#cardValue {{ color: {p['title']}; font-size: 25px; font-weight: 900; }}
    QLabel#totalStrong {{ color: {p['title']}; font-size: 22px; font-weight: 900; }}
    QLabel#dialogTitle {{ color: {p['title']}; font-size: 22px; font-weight: 900; }}

    QFrame#card, QFrame#contentCard, QFrame#dialogHeader, QFrame#summaryBox {{
      background: {p['card_bg']};
      border: 1px solid {p['card_border']};
      border-radius: 16px;
    }}
    QFrame#summaryBox {{ background: {p['summary_bg']}; }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {{
      background: {p['input_bg']};
      border: 1px solid {p['input_border']};
      border-radius: 11px;
      padding: 9px 11px;
      selection-background-color: {p['input_focus']};
      selection-color: #ffffff;
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
      border: 2px solid {p['input_focus']};
      padding: 8px 10px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}

    QPushButton {{
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 11px;
      padding: 10px 15px;
      font-weight: 800;
    }}
    QPushButton:hover {{ background: #1d4ed8; }}
    QPushButton:pressed {{ background: #1e40af; }}
    QPushButton#secondary {{ background: {p['secondary_bg']}; color: {p['secondary_fg']}; }}
    QPushButton#secondary:hover {{ background: {p['secondary_hover']}; }}
    QPushButton#danger {{ background: #dc2626; }}
    QPushButton#danger:hover {{ background: #b91c1c; }}
    QPushButton#success {{ background: #16a34a; }}
    QPushButton#success:hover {{ background: #15803d; }}
    QPushButton#accent {{ background: #7c3aed; }}
    QPushButton#accent:hover {{ background: #6d28d9; }}

    QTableWidget {{
      background: {p['card_bg']};
      alternate-background-color: {p['table_alt']};
      border: 1px solid {p['card_border']};
      border-radius: 14px;
      gridline-color: {p['table_grid']};
      selection-background-color: {p['selection_bg']};
      selection-color: {p['selection_fg']};
    }}
    QTableWidget::item {{ padding: 7px; border: none; }}
    QTableWidget::item:selected {{ background: {p['selection_bg']}; color: {p['selection_fg']}; }}
    QHeaderView::section {{
      background: {p['header_bg']};
      color: {p['header_fg']};
      padding: 10px;
      border: none;
      border-left: 1px solid {p['header_border']};
      border-bottom: 1px solid {p['header_border']};
      font-weight: 900;
    }}
    QListWidget {{
      background: {p['card_bg']};
      border: 1px solid {p['card_border']};
      border-radius: 14px;
      padding: 6px;
    }}
    QListWidget::item {{ padding: 8px; border-radius: 9px; }}
    QListWidget::item:selected {{ background: {p['selection_bg']}; color: {p['selection_fg']}; }}
    QCheckBox {{ spacing: 8px; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p['input_border']}; border-radius: 5px; min-height: 20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    """
