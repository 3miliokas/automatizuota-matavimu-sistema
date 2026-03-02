import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Automatizuota Matavimų Sistema (Prototipas)")
        self.resize(1000, 600)

        # Pagrindinis lango konteineris ir išdėstymas
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # --- KAIRĖ PUSĖ: Valdymo skydelis ---
        control_layout = QVBoxLayout()
        
        self.btn_connect = QPushButton("1. Prijungti prietaisus")
        self.btn_start = QPushButton("2. Pradėti matavimą")
        self.btn_stop = QPushButton("3. Stabdyti")
        
        # Sukuriame stilių mygtukams, kad atrodytų solidžiau
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        control_layout.addWidget(QLabel("<b>Sistemos valdymas:</b>"))
        control_layout.addWidget(self.btn_connect)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch() # Pastumia mygtukus į viršų

        # --- DEŠINĖ PUSĖ: Grafikas ---
        # Sukuriame greitąjį grafiką
        self.graph_widget = pg.PlotWidget(title="Oscilograma (Realaus laiko simuliacija)")
        self.graph_widget.setLabel('left', 'Įtampa', units='V')
        self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        self.graph_widget.showGrid(x=True, y=True)
        self.graph_widget.setYRange(-2, 2) # Fiksuojame Y ašį
        
        # Apjungiame viską į pagrindinį langą (suteikiame grafikui daugiau vietos nei mygtukams)
        main_layout.addLayout(control_layout, 1)
        main_layout.addWidget(self.graph_widget, 4)

        # --- SIMULIACIJOS LOGIKA ---
        self.x_data = []
        self.y_data = []
        # Sukuriame liniją grafike (geltonos spalvos)
        self.data_line = self.graph_widget.plot(self.x_data, self.y_data, pen='y')
        
        # Laikmatis, kuris atnaujins grafiką kas 50 milisekundžių
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_data)
        
        # Priskiriame mygtukams funkcijas
        self.btn_start.clicked.connect(self.start_measurement)
        self.btn_stop.clicked.connect(self.stop_measurement)
        
        self.time_counter = 0

    def start_measurement(self):
        """Išvalome senus duomenis ir paleidžiame laikmatį."""
        self.x_data = []
        self.y_data = []
        self.time_counter = 0
        self.timer.start(50) 

    def stop_measurement(self):
        """Sustabdome duomenų atnaujinimą."""
        self.timer.stop()

    def update_plot_data(self):
        """Ši funkcija simuliuoja duomenų gavimą iš prietaiso."""
        self.time_counter += 0.05
        self.x_data.append(self.time_counter)
        
        # Generuojame sinusinę bangą su trupučiu atsitiktinio "triukšmo" realistiškumui
        y = np.sin(2 * np.pi * 1 * self.time_counter) + np.random.normal(0, 0.1)
        self.y_data.append(y)
        
        # Išlaikome tik paskutinius 100 taškų, kad grafikas "slinktų" į kairę
        if len(self.x_data) > 100:
            self.x_data = self.x_data[1:]
            self.y_data = self.y_data[1:]
            
        # Atnaujiname kreivę grafike
        self.data_line.setData(self.x_data, self.y_data)