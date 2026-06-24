from __future__ import annotations


def build_app_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
      background: #f4f6fb;
      color: #182235;
      font-family: 'Segoe UI', 'Tahoma', 'Arial';
      font-size: 13.5px;
    }

    #sideFrame {
      background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f172a, stop:1 #111827);
      border-left: 1px solid #1f2a44;
    }
    #appTitle { color: #ffffff; font-size: 26px; font-weight: 900; letter-spacing: .3px; }
    #appSubtitle { color: #cbd5e1; font-size: 13px; }
    #sidebar { background: transparent; border: none; color: #e5eefc; outline: none; }
    #sidebar::item {
      padding: 14px 13px;
      margin: 4px 0;
      border-radius: 12px;
      color: #dbeafe;
    }
    #sidebar::item:selected {
      background: #2563eb;
      color: #ffffff;
      font-weight: 800;
    }
    #sidebar::item:hover:!selected { background: #1e293b; }

    QLabel#pageTitle { font-size: 25px; font-weight: 900; color: #0f172a; padding-bottom: 4px; }
    QLabel#sectionTitle { font-size: 16px; font-weight: 800; color: #1e293b; margin-top: 6px; }
    QLabel#hintText { color: #64748b; font-size: 12.5px; }
    QLabel#cardTitle { color: #64748b; font-size: 13px; font-weight: 700; }
    QLabel#cardValue { color: #0f172a; font-size: 25px; font-weight: 900; }
    QLabel#totalStrong { color: #0f172a; font-size: 22px; font-weight: 900; }
    QLabel#dialogTitle { color: #0f172a; font-size: 22px; font-weight: 900; }

    QFrame#card, QFrame#contentCard, QFrame#dialogHeader, QFrame#summaryBox {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
    }
    QFrame#summaryBox { background: #f8fafc; }

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 11px;
      padding: 9px 11px;
      selection-background-color: #2563eb;
      selection-color: #ffffff;
    }
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
      border: 2px solid #2563eb;
      padding: 8px 10px;
    }

    QPushButton {
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 11px;
      padding: 10px 15px;
      font-weight: 800;
    }
    QPushButton:hover { background: #1d4ed8; }
    QPushButton:pressed { background: #1e40af; }
    QPushButton#secondary { background: #e2e8f0; color: #0f172a; }
    QPushButton#secondary:hover { background: #cbd5e1; }
    QPushButton#danger { background: #dc2626; }
    QPushButton#danger:hover { background: #b91c1c; }
    QPushButton#success { background: #16a34a; }
    QPushButton#success:hover { background: #15803d; }

    QTableWidget {
      background: #ffffff;
      alternate-background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      gridline-color: #eef2f7;
      selection-background-color: #dbeafe;
      selection-color: #0f172a;
    }
    QTableWidget::item { padding: 7px; border: none; }
    QTableWidget::item:selected { background: #dbeafe; color: #0f172a; }
    QHeaderView::section {
      background: #eef2ff;
      color: #1e293b;
      padding: 9px;
      border: none;
      border-left: 1px solid #dbe2ef;
      font-weight: 900;
    }
    QListWidget {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 6px;
    }
    QListWidget::item { padding: 8px; border-radius: 9px; }
    QListWidget::item:selected { background: #dbeafe; color: #0f172a; }
    QCheckBox { spacing: 8px; }
    """
