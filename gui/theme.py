from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_dark_theme(app):
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(15, 15, 15))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    
    highlight_color = QColor(42, 130, 218)
    dark_palette.setColor(QPalette.ColorRole.Highlight, highlight_color)
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    
    app.setPalette(dark_palette)
    
    app.setStyleSheet("""
        QWidget { background-color: transparent; }
        QMainWindow { background-color: rgb(25, 25, 25); }
        QSplitter::handle { background-color: rgb(60, 60, 60); width: 2px; }
        QGroupBox {
            border: 1px solid rgb(60, 60, 60);
            background-color: rgb(35, 35, 35);
            border-radius: 3px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: white;
        }
        QTabWidget::pane {
            border: 1px solid rgb(60, 60, 60);
            background-color: rgb(35, 35, 35);
        }
        QTabBar::tab {
            background: rgb(45, 45, 45);
            color: white;
            border: 1px solid rgb(60, 60, 60);
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
            padding: 8px 12px;
            margin-right: 1px;
        }
        QTabBar::tab:selected {
            background-color: rgb(25, 25, 25);
            border-top: 3px solid rgb(42, 130, 218);
            border-bottom: 1px solid rgb(25, 25, 25);
            font-weight: bold;
        }
        QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QListWidget {
            border: 1px solid rgb(60, 60, 60);
            background-color: rgb(15, 15, 15);
            color: white;
            padding: 3px;
            selection-background-color: rgb(42, 130, 218);
        }
        QPushButton {
            background-color: rgb(50, 50, 50);
            color: white;
            border: 1px solid rgb(70, 70, 70);
            padding: 6px 15px;
            border-radius: 3px;
        }
        QPushButton:hover { background-color: rgb(65, 65, 65); }
        QPushButton:pressed { background-color: rgb(30, 30, 30); }
        QPushButton:checked {
            background-color: rgb(46, 125, 50);
            border: 1px solid rgb(27, 94, 32);
            color: white;
            font-weight: bold;
        }
    """)