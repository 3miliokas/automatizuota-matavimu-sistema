import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QDoubleSpinBox, QFormLayout, QComboBox, 
                             QTextEdit, QTabWidget, QGroupBox, QGridLayout, 
                             QProgressBar, QSpinBox)

class Ui_MainWindow:
    def setup_ui(self, MainWindow):
        MainWindow.setWindowTitle("Automatizuota Matavimų Sistema")
        MainWindow.resize(1200, 850)

        central_widget = QWidget()
        MainWindow.setCentralWidget(central_widget)
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

        # --- TAB 5: Bode Plot (Automatizacija) ---
        bode_tab = QWidget()
        bode_layout = QVBoxLayout(bode_tab)
        
        bode_settings = QFormLayout()
        self.bode_start_f = QDoubleSpinBox()
        self.bode_start_f.setRange(1, 1e8); self.bode_start_f.setValue(10); self.bode_start_f.setSuffix(" Hz")
        self.bode_stop_f = QDoubleSpinBox()
        self.bode_stop_f.setRange(10, 1e8); self.bode_stop_f.setValue(10000); self.bode_stop_f.setSuffix(" Hz")
        
        self.bode_points = QSpinBox()
        self.bode_points.setRange(2, 10000); self.bode_points.setValue(50)
        
        self.bode_amp = QDoubleSpinBox()
        self.bode_amp.setRange(0.01, 20.0); self.bode_amp.setValue(1.0); self.bode_amp.setSuffix(" Vpp")
        
        self.bode_device = QComboBox()
        self.bode_device.addItems(["Rigol MSO (Vpp)", "TTi 1604 (V)", "Escort 3136A (V)"])
        
        bode_settings.addRow("Pradinis dažnis:", self.bode_start_f)
        bode_settings.addRow("Galinis dažnis:", self.bode_stop_f)
        bode_settings.addRow("Taškų skaičius:", self.bode_points)
        bode_settings.addRow("Testinė amplitudė (Vin):", self.bode_amp)
        bode_settings.addRow("Matavimo prietaisas:", self.bode_device)
        
        btn_layout_bode = QHBoxLayout()
        self.btn_start_bode = QPushButton("Pradėti Bode skenavimą")
        self.btn_stop_bode = QPushButton("Stabdyti")
        self.btn_export_bode = QPushButton("Eksportuoti CSV")
        self.btn_start_bode.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold;")
        
        btn_layout_bode.addWidget(self.btn_start_bode)
        btn_layout_bode.addWidget(self.btn_stop_bode)
        btn_layout_bode.addWidget(self.btn_export_bode)
        
        self.bode_progress = QProgressBar()
        self.bode_progress.setValue(0)
        
        self.bode_graph = pg.PlotWidget(title="Amplitudės-Dažnio Charakteristika")
        self.bode_graph.setLabel('left', 'Stiprinimas', units='dB')
        self.bode_graph.setLabel('bottom', 'Dažnis', units='Hz (Log)')
        self.bode_graph.setLogMode(x=True, y=False)
        self.bode_graph.showGrid(x=True, y=True)
        
        bode_layout.addLayout(bode_settings)
        bode_layout.addLayout(btn_layout_bode)
        bode_layout.addWidget(self.bode_progress)
        bode_layout.addWidget(self.bode_graph)

        tabs.addTab(gen_tab, "Generatorius (SDG)")
        tabs.addTab(osc_tab, "Oscilografas (MSO)")
        tabs.addTab(tti_tab, "Multimetras 1 (TTi)")
        tabs.addTab(escort_tab, "Multimetras 2 (Escort)")
        tabs.addTab(bode_tab, "Bode Plot (Auto)")

        # 3. Bendras valdymas
        self.btn_start_stream = QPushButton("Pradėti gyvą rodymą")
        self.btn_stop_stream = QPushButton("Stabdyti gyvą rodymą")
        self.btn_export = QPushButton("Eksportuoti CSV")
        self.btn_start_stream.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_stop_stream.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(150)
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