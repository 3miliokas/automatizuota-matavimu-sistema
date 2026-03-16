import csv
from datetime import datetime
import pyqtgraph as pg
import numpy as np
import pyvisa
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox, QFormLayout, 
                             QComboBox, QMessageBox, QTextEdit, QFileDialog)
from PyQt6.QtCore import QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Automatizuota Matavimų Sistema")
        self.resize(1100, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # --- KAIRĖ PUSĖ: Valdymo skydelis ---
        control_layout = QVBoxLayout()
        
        # 1. Prietaisų paieška
        self.device_combo = QComboBox()
        self.device_combo.addItem("Neprijungta / Nėra prietaisų")
        
        self.btn_scan = QPushButton("1. Ieškoti prietaisų (Scan)")
        self.btn_scan.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        # 2. Nustatymų forma
        settings_layout = QFormLayout()
        self.amplitude_input = QDoubleSpinBox()
        self.amplitude_input.setRange(0.1, 20.0)
        self.amplitude_input.setValue(1.0)
        self.amplitude_input.setSuffix(" V")
        
        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setRange(0.1, 1000.0)
        self.frequency_input.setValue(1.0)
        self.frequency_input.setSuffix(" Hz")

        settings_layout.addRow("Amplitudė:", self.amplitude_input)
        settings_layout.addRow("Dažnis:", self.frequency_input)
        
        # 3. Valdymo mygtukai
        self.btn_start = QPushButton("2. Pradėti matavimą")
        self.btn_stop = QPushButton("3. Stabdyti")
        self.btn_export = QPushButton("4. Eksportuoti į CSV")
        
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.btn_export.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_export.setEnabled(False) # Aktyvuojamas tik sustabdžius
        
        # 4. Statistika
        self.lbl_vpp = QLabel("Vpp (Pikas-Pikas): 0.00 V")
        self.lbl_vrms = QLabel("Vrms (Efektinė): 0.00 V")
        self.lbl_vpp.setStyleSheet("font-weight: bold; color: #333;")
        self.lbl_vrms.setStyleSheet("font-weight: bold; color: #333;")

        # 5. Sistemos žurnalas (Log)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(150)
        self.log_console.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")

        # Elementų sudėjimas į kairį skydelį
        control_layout.addWidget(QLabel("<b>Aparatūra:</b>"))
        control_layout.addWidget(self.btn_scan)
        control_layout.addWidget(self.device_combo)
        control_layout.addWidget(QLabel("<br><b>Sistemos parametrai:</b>"))
        control_layout.addLayout(settings_layout)
        control_layout.addWidget(QLabel("<br><b>Valdymas:</b>"))
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.btn_export)
        control_layout.addWidget(QLabel("<br><b>Gyvi rodmenys:</b>"))
        control_layout.addWidget(self.lbl_vpp)
        control_layout.addWidget(self.lbl_vrms)
        control_layout.addStretch()
        control_layout.addWidget(QLabel("<b>Sistemos žurnalas:</b>"))
        control_layout.addWidget(self.log_console)
        
        # Mygtukų signalai
        self.btn_scan.clicked.connect(self.scan_devices)
        self.btn_start.clicked.connect(self.start_measurement)
        self.btn_stop.clicked.connect(self.stop_measurement)
        self.btn_export.clicked.connect(self.export_csv)

        # --- DEŠINĖ PUSĖ: Grafikas ---
        self.graph_widget = pg.PlotWidget(title="Oscilograma (Realaus laiko simuliacija)")
        self.graph_widget.setLabel('left', 'Įtampa', units='V')
        self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        self.graph_widget.showGrid(x=True, y=True)
        
        main_layout.addLayout(control_layout, 1)
        main_layout.addWidget(self.graph_widget, 3)

        # --- SIMULIACIJOS LOGIKA ---
        self.x_data = []
        self.y_data = []
        self.data_line = self.graph_widget.plot(self.x_data, self.y_data, pen='y')
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_data)
        self.time_counter = 0

        self.log_msg("Sistema sėkmingai inicializuota.")

    def log_msg(self, text):
        """Patalpina žinutę į vidinį sistemos žurnalą su laiko žyma."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {text}")

    def scan_devices(self):
        self.device_combo.clear()
        self.log_msg("Pradedama VISA prietaisų paieška...")
        try:
            rm = pyvisa.ResourceManager()
            instruments = rm.list_resources()
            
            if instruments:
                self.device_combo.addItems(instruments)
                self.log_msg(f"Rasta prietaisų: {len(instruments)}")
            else:
                self.device_combo.addItem("Prietaisų nerasta")
                self.log_msg("Klaida: Prietaisų nerasta. Patikrinkite laidus.")
                
        except Exception as e:
            self.device_combo.addItem("Klaida: VISA neįdiegta")
            self.log_msg(f"Klaida inicijuojant PyVISA: {str(e)}")

    def start_measurement(self):
        self.x_data = []
        self.y_data = []
        self.time_counter = 0
        self.btn_export.setEnabled(False)
        self.log_msg(f"Matavimas pradėtas. Parametrai: {self.amplitude_input.value()}V, {self.frequency_input.value()}Hz.")
        self.timer.start(50) 

    def stop_measurement(self):
        self.timer.stop()
        self.btn_export.setEnabled(True)
        self.log_msg("Matavimas sustabdytas. Duomenys paruošti eksportui.")

    def export_csv(self):
        """Eksportuoja masyvus į .csv failą."""
        if not self.x_data:
            self.log_msg("Klaida: Nėra duomenų eksportavimui.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Išsaugoti duomenis", "", "CSV failai (*.csv)")
        if filename:
            try:
                with open(filename, mode='w', newline='') as file:
                    writer = csv.writer(file, delimiter=',')
                    writer.writerow(["Laikas_s", "Itampa_V"])
                    for x, y in zip(self.x_data, self.y_data):
                        writer.writerow([round(x, 4), round(y, 4)])
                self.log_msg(f"Duomenys eksportuoti: {filename}")
            except Exception as e:
                self.log_msg(f"Klaida išsaugant failą: {str(e)}")

    def update_plot_data(self):
        self.time_counter += 0.05
        self.x_data.append(self.time_counter)
        
        amp = self.amplitude_input.value()
        freq = self.frequency_input.value()

        self.graph_widget.setYRange(-amp * 1.2, amp * 1.2)
        
        y = amp * np.sin(2 * np.pi * freq * self.time_counter) + np.random.normal(0, 0.1)
        self.y_data.append(y)
        
        # Ribojame iki 200 taškų, kad neužkištų RAM simuliacijos metu
        if len(self.x_data) > 200:
            self.x_data = self.x_data[1:]
            self.y_data = self.y_data[1:]
            
        self.data_line.setData(self.x_data, self.y_data)

        # Skaičiuojame ir atnaujiname gyvą statistiką
        current_vpp = np.max(self.y_data) - np.min(self.y_data)
        current_vrms = np.sqrt(np.mean(np.square(self.y_data)))
        
        self.lbl_vpp.setText(f"Vpp (Pikas-Pikas): {current_vpp:.2f} V")
        self.lbl_vrms.setText(f"Vrms (Efektinė): {current_vrms:.2f} V")