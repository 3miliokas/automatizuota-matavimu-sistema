from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Automatizuota Matavimų Sistema (Testas)")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        test_label = QLabel("Sistemos grafinė sąsaja sėkmingai pasileido!")
        test_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(test_label)