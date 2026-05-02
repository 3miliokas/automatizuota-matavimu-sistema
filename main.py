import sys
from PyQt6.QtWidgets import QApplication

from gui.theme import apply_dark_theme
from gui.main_window import MainWindow

def main():
    """Pagrindinė programos paleidimo funkcija."""
    app = QApplication(sys.argv)
    
    # Pritaikome profesionalią tamsią temą
    apply_dark_theme(app)
    
    # Inicijuojame ir parodome pagrindinį langą
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from gui.theme import apply_dark_theme
    
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())