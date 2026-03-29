import csv
from datetime import datetime
import pyqtgraph as pg
import pyvisa
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox, QFormLayout, 
                             QComboBox, QTextEdit, QFileDialog, QTabWidget, QGroupBox, QGridLayout)
from PyQt6.QtCore import QTimer

from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
import serial.tools.list_ports
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automatizuota Matavimų Sistema")
        self.resize(1200, 850)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- KAIRĖ PUSĖ: Valdymo skydelis ---
        left_panel = QVBoxLayout()
        
        # 1. Ryšio skydelis
        conn_group = QGroupBox("Aparatūros Ryšys")
        conn_layout = QFormLayout()
        self.btn_scan = QPushButton("Skenuoti VISA ir COM")
        self.combo_gen = QComboBox()
        self.combo_osc = QComboBox()
        self.combo_tti = QComboBox()
        self.combo_escort = QComboBox()
        
        conn_layout.addRow(self.btn_scan)
        conn_layout.addRow("Generatorius:", self.combo_gen)
        conn_layout.addRow("Oscilografas:", self.combo_osc)
        conn_layout.addRow("TTi 1604 (COM):", self.combo_tti)
        conn_layout.addRow("Escort 3136A (COM):", self.combo_escort)
        conn_group.setLayout(conn_layout)

        # 2. Skirtukai (Tabs) prietaisų valdymui
        tabs = QTabWidget()
        
        # --- TAB 1: Generatorius ---
        gen_tab = QWidget()
        gen_layout = QFormLayout(gen_tab)
        
        self.wave_type = QComboBox()
        self.wave_type.addItems(["Sine", "Square", "Ramp", "Pulse", "Noise", "Arb"])
        self.amp_in = QDoubleSpinBox()
        self.amp_in.setRange(0.002, 20.0); self.amp_in.setValue(1.0); self.amp_in.setSuffix(" Vpp")
        self.offset_in = QDoubleSpinBox()
        self.offset_in.setRange(-10.0, 10.0); self.offset_in.setSuffix(" Vdc")
        
        self.freq_in = QDoubleSpinBox()
        self.freq_in.setRange(0.001, 999.0); self.freq_in.setValue(10.0); self.freq_in.setDecimals(3)
        self.freq_unit = QComboBox()
        self.freq_unit.addItems(["Hz", "kHz", "MHz"]); self.freq_unit.setCurrentText("kHz")
        f_box = QHBoxLayout(); f_box.addWidget(self.freq_in); f_box.addWidget(self.freq_unit); f_box.setContentsMargins(0,0,0,0)
        f_widget = QWidget(); f_widget.setLayout(f_box)

        self.phase_in = QDoubleSpinBox(); self.phase_in.setRange(0, 360); self.phase_in.setSuffix(" °")
        self.duty_in = QDoubleSpinBox(); self.duty_in.setRange(0.1, 99.9); self.duty_in.setValue(50); self.duty_in.setSuffix(" %")
        self.sym_in = QDoubleSpinBox(); self.sym_in.setRange(0, 100); self.sym_in.setValue(50); self.sym_in.setSuffix(" %")

        gen_layout.addRow("Tipas:", self.wave_type)
        gen_layout.addRow("Dažnis:", f_widget)
        gen_layout.addRow("Amplitudė:", self.amp_in)
        gen_layout.addRow("Poslinkis:", self.offset_in)
        gen_layout.addRow("Fazė:", self.phase_in)
        gen_layout.addRow("Darbo ciklas:", self.duty_in)
        gen_layout.addRow("Simetrija:", self.sym_in)
        
        self.btn_apply_gen = QPushButton("Nustatyti Generatorių")
        self.btn_apply_gen.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        gen_layout.addRow(self.btn_apply_gen)

        # --- TAB 2: Oscilografas ---
        osc_tab = QWidget()
        osc_layout = QVBoxLayout(osc_tab)
        
        ctrl_layout = QHBoxLayout()
        self.btn_auto = QPushButton("Auto-Scale")
        self.btn_run = QPushButton("Run")
        self.btn_stop_osc = QPushButton("Stop")
        self.btn_screenshot = QPushButton("Išsaugoti nuotrauką")
        self.btn_screenshot.setStyleSheet("background-color: #673AB7; color: white; font-weight: bold;")
        
        ctrl_layout.addWidget(self.btn_auto)
        ctrl_layout.addWidget(self.btn_run)
        ctrl_layout.addWidget(self.btn_stop_osc)
        ctrl_layout.addWidget(self.btn_screenshot)
        
        meas_group = QGroupBox("Aparatūriniai matavimai (iš Rigol)")
        meas_grid = QGridLayout()
        
        self.lbl_meas_vpp = QLabel("Vpp: -")
        self.lbl_meas_vmax = QLabel("Vmax: -")
        self.lbl_meas_vmin = QLabel("Vmin: -")
        self.lbl_meas_freq = QLabel("Dažnis: -")
        self.lbl_meas_rise = QLabel("Rise Time: -")
        self.lbl_meas_fall = QLabel("Fall Time: -")
        
        for lbl in [self.lbl_meas_vpp, self.lbl_meas_vmax, self.lbl_meas_vmin, 
                    self.lbl_meas_freq, self.lbl_meas_rise, self.lbl_meas_fall]:
            lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #2196F3;")
            
        meas_grid.addWidget(self.lbl_meas_vpp, 0, 0)
        meas_grid.addWidget(self.lbl_meas_vmax, 1, 0)
        meas_grid.addWidget(self.lbl_meas_vmin, 2, 0)
        meas_grid.addWidget(self.lbl_meas_freq, 0, 1)
        meas_grid.addWidget(self.lbl_meas_rise, 1, 1)
        meas_grid.addWidget(self.lbl_meas_fall, 2, 1)
        
        self.btn_meas_all = QPushButton("Atnaujinti matavimus")
        meas_grid.addWidget(self.btn_meas_all, 3, 0, 1, 2)
        meas_group.setLayout(meas_grid)

        osc_layout.addLayout(ctrl_layout)
        osc_layout.addWidget(meas_group)
        osc_layout.addStretch()

        # --- TAB 3: TTi 1604 Multimetras ---
        tti_tab = QWidget()
        tti_layout = QVBoxLayout(tti_tab)
        
        self.btn_tti_v = QPushButton("Matuoti Įtampą (V)")
        self.btn_tti_a = QPushButton("Matuoti Srovę (A)")
        self.lbl_tti_res = QLabel("Reikšmė: -")
        self.lbl_tti_res.setStyleSheet("font-weight: bold; font-size: 16px; color: #4CAF50;")
        
        tti_layout.addWidget(self.btn_tti_v)
        tti_layout.addWidget(self.btn_tti_a)
        tti_layout.addWidget(self.lbl_tti_res)
        tti_layout.addStretch()
        
        # --- TAB 4: Escort 3136A Multimetras ---
        escort_tab = QWidget()
        escort_layout = QVBoxLayout(escort_tab)
        
        self.btn_escort_v = QPushButton("Matuoti Įtampą (V)")
        self.btn_escort_a = QPushButton("Matuoti Srovę (A)")
        self.lbl_escort_res = QLabel("Reikšmė: -")
        self.lbl_escort_res.setStyleSheet("font-weight: bold; font-size: 16px; color: #FF9800;")
        
        escort_layout.addWidget(self.btn_escort_v)
        escort_layout.addWidget(self.btn_escort_a)
        escort_layout.addWidget(self.lbl_escort_res)
        escort_layout.addStretch()

        tabs.addTab(gen_tab, "Generatorius (SDG)")
        tabs.addTab(osc_tab, "Oscilografas (MSO)")
        tabs.addTab(tti_tab, "Multimetras 1 (TTi)")
        tabs.addTab(escort_tab, "Multimetras 2 (Escort)")

        # 3. Bendras valdymas
        self.btn_start_stream = QPushButton("Pradėti gyvą rodymą")
        self.btn_stop_stream = QPushButton("Stabdyti gyvą rodymą")
        self.btn_export = QPushButton("Eksportuoti CSV")
        self.btn_start_stream.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_stop_stream.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(200)
        self.log_console.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")

        left_panel.addWidget(conn_group)
        left_panel.addWidget(tabs)
        left_panel.addWidget(self.btn_start_stream)
        left_panel.addWidget(self.btn_stop_stream)
        left_panel.addWidget(self.btn_export)
        left_panel.addWidget(QLabel("<b>Sistemos žurnalas:</b>"))
        left_panel.addWidget(self.log_console)

        # --- DEŠINĖ PUSĖ: Grafikas ---
        self.graph_widget = pg.PlotWidget(title="Oscilograma (Realūs Duomenys iš Rigol)")
        self.graph_widget.setLabel('left', 'Įtampa', units='V')
        self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        self.graph_widget.showGrid(x=True, y=True)
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addWidget(self.graph_widget, 3)

        self.x_data, self.y_data = [], []
        self.data_line = self.graph_widget.plot(self.x_data, self.y_data, pen='y')
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_from_rigol)

        # Signalai
        self.btn_scan.clicked.connect(self.scan_devices)
        self.btn_apply_gen.clicked.connect(self.apply_generator)
        self.btn_auto.clicked.connect(self.trigger_autoscale)
        self.btn_run.clicked.connect(lambda: self.control_osc("run"))
        self.btn_stop_osc.clicked.connect(lambda: self.control_osc("stop"))
        self.btn_meas_all.clicked.connect(self.fetch_all_measurements)
        self.btn_screenshot.clicked.connect(self.save_rigol_screenshot)
        self.btn_start_stream.clicked.connect(self.start_stream)
        self.btn_stop_stream.clicked.connect(self.stop_stream)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_tti_v.clicked.connect(lambda: self.fetch_tti("V"))
        self.btn_tti_a.clicked.connect(lambda: self.fetch_tti("A"))
        self.btn_escort_v.clicked.connect(lambda: self.fetch_escort("V"))
        self.btn_escort_a.clicked.connect(lambda: self.fetch_escort("A"))

    # --- FUNKCIJOS ---

    def log_msg(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {text}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def format_eng(self, val, unit="V"):
        if val is None or val > 1e15: return "N/A" 
        if val == 0: return f"0.00 {unit}"
        
        abs_val = abs(val)
        if abs_val >= 1e9: return f"{val/1e9:.2f} G{unit}"
        if abs_val >= 1e6: return f"{val/1e6:.2f} M{unit}"
        if abs_val >= 1e3: return f"{val/1e3:.2f} k{unit}"
        if abs_val >= 1: return f"{val:.2f} {unit}"
        if abs_val >= 1e-3: return f"{val*1e3:.2f} m{unit}"
        if abs_val >= 1e-6: return f"{val*1e6:.2f} µ{unit}"
        if abs_val >= 1e-9: return f"{val*1e9:.2f} n{unit}"
        return f"{val:.2e} {unit}"

    def scan_devices(self):
        self.combo_gen.clear(); self.combo_osc.clear(); self.combo_tti.clear(); self.combo_escort.clear()
        self.log_msg("Skenuojama VISA ir COM prievadai...")
        
        # VISA skenavimas
        rm = pyvisa.ResourceManager()
        for addr in rm.list_resources():
            try:
                inst = rm.open_resource(addr)
                inst.timeout = 500
                idn = inst.query("*IDN?").strip()
                inst.close()
                name = idn.split(',')[1] if len(idn.split(',')) > 1 else idn
                
                if "SDG" in idn:
                    self.combo_gen.addItem(f"{name} [{addr}]", addr)
                elif "DS1" in idn or "MSO" in idn:
                    self.combo_osc.addItem(f"{name} [{addr}]", addr)
            except Exception:
                pass
                
        # COM skenavimas
        ports = serial.tools.list_ports.comports()
        for port in ports:
            port_info = f"{port.device} - {port.description}"
            self.combo_tti.addItem(port_info, port.device)
            self.combo_escort.addItem(port_info, port.device)
            
        self.log_msg("Skenavimas baigtas.")

    def get_freq_hz(self):
        m = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
        return self.freq_in.value() * m[self.freq_unit.currentText()]

    def apply_generator(self):
        addr = self.combo_gen.currentData()
        if not addr: return self.log_msg("Nepasirinktas generatorius.")
        try:
            gen = SiglentSDG(addr)
            gen.apply_waveform(self.wave_type.currentText(), self.get_freq_hz(), 
                               self.amp_in.value(), self.offset_in.value(),
                               self.phase_in.value(), self.duty_in.value(), self.sym_in.value())
            gen.close()
            self.log_msg("Generatorius atnaujintas.")
        except Exception as e:
            self.log_msg(f"Klaida atnaujinant generatorių: {e}")

    def trigger_autoscale(self):
        addr = self.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.auto_scale()
            osc.close()
            self.log_msg("Rigol Auto-Scale iškviestas.")
        except Exception as e: self.log_msg(f"Klaida (Auto-Scale): {e}")

    def control_osc(self, state):
        addr = self.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.run() if state == "run" else osc.stop()
            osc.close()
        except Exception as e: self.log_msg(f"Klaida (Run/Stop): {e}")

    def fetch_all_measurements(self):
        addr = self.combo_osc.currentData()
        if not addr: return
        
        was_streaming = self.timer.isActive()
        if was_streaming:
            self.timer.stop()

        self.log_msg("Skaitomi aparatūriniai matavimai...")
        try:
            osc = RigolMSO(addr)
            vpp = osc.get_measure("VPP")
            vmax = osc.get_measure("VMAX")
            vmin = osc.get_measure("VMIN")
            freq = osc.get_measure("FREQ")
            rise = osc.get_measure("RISetime")
            fall = osc.get_measure("FALLtime")
            osc.close()
            
            self.lbl_meas_vpp.setText(f"Vpp: {self.format_eng(vpp, 'V')}")
            self.lbl_meas_vmax.setText(f"Vmax: {self.format_eng(vmax, 'V')}")
            self.lbl_meas_vmin.setText(f"Vmin: {self.format_eng(vmin, 'V')}")
            self.lbl_meas_freq.setText(f"Dažnis: {self.format_eng(freq, 'Hz')}")
            self.lbl_meas_rise.setText(f"Rise Time: {self.format_eng(rise, 's')}")
            self.lbl_meas_fall.setText(f"Fall Time: {self.format_eng(fall, 's')}")
            self.log_msg("Matavimai sėkmingai atnaujinti.")
            
        except Exception as e: 
            self.log_msg(f"Klaida skaitant matavimus: {e}")

        if was_streaming:
            self.timer.start(500)

    def start_stream(self):
        if not self.combo_osc.currentData():
            return self.log_msg("Klaida: Nepasirinktas oscilografas.")
        self.timer.start(500) 
        self.log_msg("Duomenų srautas pradėtas.")

    def stop_stream(self):
        self.timer.stop()
        self.log_msg("Duomenų srautas sustabdytas.")

    def update_plot_from_rigol(self):
        addr = self.combo_osc.currentData()
        try:
            osc = RigolMSO(addr)
            t, v = osc.get_waveform_data(channel=1)
            osc.close()
            
            self.x_data, self.y_data = t, v
            self.data_line.setData(self.x_data, self.y_data)
        except pyvisa.errors.VisaIOError:
            pass 
        except Exception:
            pass

    def export_csv(self):
        if not self.x_data: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                # Naudojame vadovo antraštes dėl suderinamumo su išoriniais analizės skriptais
                w.writerow(["Time", "Voltage"])
                for x, y in zip(self.x_data, self.y_data):
                    # Formatuojame skaičius moksliniu formatu su 10 ženklų po kablelio tikslumu
                    w.writerow([f"{x:.10e}", f"{y:.10e}"])
            self.log_msg("Eksportuota sėkmingai.")

    def save_rigol_screenshot(self):
        addr = self.combo_osc.currentData()
        if not addr: 
            return self.log_msg("Klaida: Nepasirinktas oscilografas.")
        
        was_streaming = self.timer.isActive()
        if was_streaming:
            self.timer.stop()

        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti ekrano nuotrauką", "rigol_screen.png", "PNG failai (*.png)")
        if fn:
            self.log_msg("Nuskaitoma ekrano nuotrauka iš Rigol (tai gali užtrukti)...")
            try:
                osc = RigolMSO(addr)
                img_data = osc.get_screenshot()
                osc.close()
                
                with open(fn, "wb") as f:
                    f.write(img_data)
                self.log_msg(f"Nuotrauka sėkmingai išsaugota: {fn}")
            except Exception as e:
                self.log_msg(f"Klaida išsaugant nuotrauką: {e}")

        if was_streaming:
            self.timer.start(500)

    def fetch_tti(self, mode):
        port = self.combo_tti.currentData()
        if not port:
            return self.log_msg("Klaida: Nepasirinktas TTi COM prievadas.")
            
        self.log_msg(f"Jungiamasi prie TTi 1604 ({port})...")
        try:
            tti = TTi1604(port)
            val = tti.get_voltage() if mode == "V" else tti.get_current()
            unit = "V" if mode == "V" else "A"
            tti.close()
            
            if val is not None:
                self.lbl_tti_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
                self.log_msg(f"TTi matavimas: {self.format_eng(val, unit)}")
            else:
                self.lbl_tti_res.setText("Reikšmė: Klaida (Timeout)")
                self.log_msg("Klaida: TTi neatsakė per nustatytą laiką.")
        except Exception as e:
            self.log_msg(f"Klaida komunikuojant su TTi: {e}")

    def fetch_escort(self, mode):
        port = self.combo_escort.currentData()
        if not port:
            return self.log_msg("Klaida: Nepasirinktas Escort COM prievadas.")
            
        self.log_msg(f"Jungiamasi prie Escort 3136A ({port})...")
        try:
            escort = Escort3136A(port)
            val = escort.get_voltage_dc() if mode == "V" else escort.get_current_dc()
            unit = "V" if mode == "V" else "A"
            escort.close()
            
            if val is not None:
                self.lbl_escort_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
                self.log_msg(f"Escort matavimas: {self.format_eng(val, unit)}")
            else:
                self.lbl_escort_res.setText("Reikšmė: Nepavyko nuskaityti")
                self.log_msg("Klaida: Escort negrąžino tinkamo atsakymo.")
        except Exception as e:
            self.log_msg(f"Klaida komunikuojant su Escort: {e}")