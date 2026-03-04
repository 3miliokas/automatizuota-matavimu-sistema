import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QFormLayout
from PyQt6.QtCore import QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Automatizuota Matavimų Sistema (Prototipas)")
        self.resize(1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # --- KAIRĖ PUSĖ: Valdymo skydelis ---
        control_layout = QVBoxLayout()
        
        # Nustatymų forma
        settings_layout = QFormLayout()
        self.amplitude_input = QDoubleSpinBox()
        self.amplitude_input.setRange(0.1, 10.0)
        self.amplitude_input.setValue(1.0)
        self.amplitude_input.setSuffix(" V")
        
        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setRange(0.1, 100.0)
        self.frequency_input.setValue(1.0)
        self.frequency_input.setSuffix(" Hz")

        settings_layout.addRow("Amplitudė:", self.amplitude_input)
        settings_layout.addRow("Dažnis:", self.frequency_input)
        
        # Mygtukai
        self.btn_connect = QPushButton("1. Prijungti prietaisus")
        self.btn_start = QPushButton("2. Pradėti matavimą")
        self.btn_stop = QPushButton("3. Stabdyti")
        
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        control_layout.addWidget(QLabel("<b>Sistemos parametrai:</b>"))
        control_layout.addLayout(settings_layout)
        control_layout.addWidget(QLabel("<b>Valdymas:</b>"))
        control_layout.addWidget(self.btn_connect)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch()

        # --- DEŠINĖ PUSĖ: Grafikas ---
        self.graph_widget = pg.PlotWidget(title="Oscilograma (Realaus laiko simuliacija)")
        self.graph_widget.setLabel('left', 'Įtampa', units='V')
        self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        self.graph_widget.showGrid(x=True, y=True)
        #self.graph_widget.setYRange(-5, 5) 
        
        main_layout.addLayout(control_layout, 1)
        main_layout.addWidget(self.graph_widget, 4)

        # --- SIMULIACIJOS LOGIKA ---
        self.x_data = []
        self.y_data = []
        self.data_line = self.graph_widget.plot(self.x_data, self.y_data, pen='y')
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_data)
        
        self.btn_start.clicked.connect(self.start_measurement)
        self.btn_stop.clicked.connect(self.stop_measurement)
        
        self.time_counter = 0

    def start_measurement(self):
        self.x_data = []
        self.y_data = []
        self.time_counter = 0
        self.timer.start(50) 

    def stop_measurement(self):
        self.timer.stop()

    def update_plot_data(self):
        self.time_counter += 0.05
        self.x_data.append(self.time_counter)
        
        # Naudojame vartotojo įvestus parametrus
        amp = self.amplitude_input.value()
        freq = self.frequency_input.value()

        # Dinaminis mastelis su 20% atsarga
        self.graph_widget.setYRange(-amp * 1.2, amp * 1.2)
        
        y = amp * np.sin(2 * np.pi * freq * self.time_counter) + np.random.normal(0, 0.1)
        self.y_data.append(y)
        
        if len(self.x_data) > 100:
            self.x_data = self.x_data[1:]
            self.y_data = self.y_data[1:]
            
        self.data_line.setData(self.x_data, self.y_data)