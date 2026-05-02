from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_dark_theme(app):
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    app.setPalette(dark_palette)

    flat_css = """
        QWidget {
            font-size: 12px;
        }
        QGroupBox {
            border: 1px solid rgb(60, 60, 60);
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px;
            color: #2A82DA;
            font-weight: bold;
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
            padding: 6px 10px;
            margin-right: 1px;
            border-radius: 0px;
        }
        QTabBar::tab:selected {
            background-color: rgb(25, 25, 25);
            border-top: 2px solid rgb(42, 130, 218);
            font-weight: bold;
        }
        QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QListWidget, QTableWidget {
            border: 1px solid rgb(60, 60, 60);
            background-color: rgb(15, 15, 15);
            color: white;
            padding: 2px;
            border-radius: 0px;
            selection-background-color: rgb(156, 39, 176);
        }
        QListView {
            background-color: rgb(25, 25, 25);
            color: white;
            outline: 0;
            border: 1px solid rgb(60, 60, 60);
        }
        QListView::item:selected, QListView::item:hover {
            background-color: rgb(156, 39, 176);
            color: white;
        }
        QTableView::item:selected {
            background-color: rgb(156, 39, 176);
            color: white;
        }
        QPushButton {
            border-radius: 0px;
            border: 1px solid rgb(60, 60, 60);
        }
    """
    app.setStyleSheet(flat_css)

STYLE_PRIMARY = "QPushButton { background-color: #2980B9; color: white; font-weight: bold; padding: 6px; border: none; } QPushButton:hover { background-color: #3498DB; }"
STYLE_SUCCESS = "QPushButton { background-color: #27AE60; color: white; font-weight: bold; padding: 6px; border: none; } QPushButton:hover { background-color: #2ECC71; }"
STYLE_DANGER = "QPushButton { background-color: #C0392B; color: white; font-weight: bold; padding: 6px; border: none; } QPushButton:hover { background-color: #E74C3C; }"
STYLE_NORMAL = "QPushButton { background-color: #454545; color: white; padding: 6px; border: 1px solid #555; } QPushButton:hover { background-color: #555; }"
STYLE_ACTIVE = "QPushButton { background-color: #27AE60; color: white; font-weight: bold; padding: 6px; border: none; }"
STYLE_EXPORT = "QPushButton { background-color: #8E44AD; color: white; font-weight: bold; padding: 6px; border: none; } QPushButton:hover { background-color: #9B59B6; }"
STYLE_LCD_DC = "font-size: 24px; font-weight: bold; color: #4CAF50; background: black; padding: 5px; border: 1px solid #333; text-align: center;"
STYLE_LCD_AC = "font-size: 24px; font-weight: bold; color: #FFA500; background: black; padding: 5px; border: 1px solid #333; text-align: center;"