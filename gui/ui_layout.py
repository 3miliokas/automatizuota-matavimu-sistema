import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QDoubleSpinBox, QFormLayout, QComboBox, 
                             QTextEdit, QTabWidget, QGroupBox, QGridLayout, 
                             QProgressBar, QSpinBox, QLineEdit, QSplitter,
                             QScrollArea, QFrame, QHeaderView, QTableWidget)
from PyQt6.QtCore import Qt

class Ui_MainWindow:
    def setup_ui(self, MainWindow):
        MainWindow.setWindowTitle("Automatizuota Matavimų Sistema")
        MainWindow.resize(1400, 900)

        central_widget = QWidget()
        MainWindow.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMinimumWidth(450)
        scroll_area.setMaximumWidth(600)
        
        container = QWidget()
        left_layout = QVBoxLayout(container)

        conn_group = QGroupBox("Bendra Informacija")
        conn_layout = QFormLayout(conn_group)
        self.btn_scan = QPushButton("Skenuoti VISA ir COM")
        self.combo_gen = QComboBox(); self.combo_osc = QComboBox()
        self.combo_tti = QComboBox(); self.combo_escort = QComboBox()
        self.input_serial = QLineEdit(); self.input_serial.setPlaceholderText("Pvz.: DUT-12345")
        self.btn_generate_pdf = QPushButton("Generuoti PDF Protokolą")
        
        style_indigo = "QPushButton {background-color: #3F51B5; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #5C6BC0;} QPushButton:pressed {background-color: #283593;}"
        style_purple = "QPushButton {background-color: #9C27B0; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #AB47BC;} QPushButton:pressed {background-color: #7B1FA2;}"
        style_blue = "QPushButton {background-color: #2196F3; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #42A5F5;} QPushButton:pressed {background-color: #1976D2;}"
        style_green = "QPushButton {background-color: #4CAF50; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #66BB6A;} QPushButton:pressed {background-color: #388E3C;}"
        style_red = "QPushButton {background-color: #F44336; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #EF5350;} QPushButton:pressed {background-color: #D32F2F;}"
        style_gray = "QPushButton {background-color: #607D8B; color: white; border: none; font-weight: bold; padding: 6px; border-radius: 3px;} QPushButton:hover {background-color: #78909C;} QPushButton:pressed {background-color: #455A64;}"
        
        style_toggle = """
            QPushButton {background-color: #455A64; color: white; border: none; font-weight: bold; padding: 8px; border-radius: 3px;}
            QPushButton:hover {background-color: #546E7A;}
            QPushButton:checked {background-color: #4CAF50;}
            QPushButton:checked:hover {background-color: #66BB6A;}
        """
        
        self.btn_scan.setStyleSheet(style_indigo)
        self.btn_generate_pdf.setStyleSheet(style_indigo)
        
        conn_layout.addRow(self.btn_scan)
        conn_layout.addRow("Gen (SDG):", self.combo_gen)
        conn_layout.addRow("Osc (MSO):", self.combo_osc)
        conn_layout.addRow("TTi (COM):", self.combo_tti)
        conn_layout.addRow("Escort (COM):", self.combo_escort)
        conn_layout.addRow("Serijos Nr.:", self.input_serial)
        conn_layout.addRow(self.btn_generate_pdf)
        left_layout.addWidget(conn_group)

        self.ctrl_tabs = QTabWidget()
        
        # 1. Generatorius
        gen_tab = QWidget(); gen_layout = QFormLayout(gen_tab)
        self.gen_ch_select = QComboBox(); self.gen_ch_select.addItems(["CH1", "CH2"])
        self.wave_type = QComboBox(); self.wave_type.addItems(["Sine", "Square", "Ramp", "Pulse", "Noise", "Arb"])
        
        self.freq_in = QDoubleSpinBox(); self.freq_in.setRange(0.001, 999.0); self.freq_in.setValue(10.0); self.freq_in.setDecimals(3)
        self.freq_unit = QComboBox(); self.freq_unit.addItems(["Hz", "kHz", "MHz"]); self.freq_unit.setCurrentText("kHz")
        f_box = QHBoxLayout(); f_box.addWidget(self.freq_in); f_box.addWidget(self.freq_unit); f_box.setContentsMargins(0,0,0,0)
        f_widget = QWidget(); f_widget.setLayout(f_box)
        
        self.amp_in = QDoubleSpinBox(); self.amp_in.setRange(0.002, 20.0); self.amp_in.setValue(1.0); self.amp_in.setSuffix(" Vpp")
        self.offset_in = QDoubleSpinBox(); self.offset_in.setRange(-10.0, 10.0); self.offset_in.setSuffix(" Vdc")
        
        self.phase_in = QDoubleSpinBox(); self.phase_in.setRange(0, 360); self.phase_in.setDecimals(1); self.phase_in.setSingleStep(0.1); self.phase_in.setSuffix(" °")
        self.duty_in = QDoubleSpinBox(); self.duty_in.setRange(0.1, 99.9); self.duty_in.setDecimals(1); self.duty_in.setSingleStep(0.1); self.duty_in.setValue(50.0); self.duty_in.setSuffix(" %")
        self.sym_in = QDoubleSpinBox(); self.sym_in.setRange(0.0, 100.0); self.sym_in.setDecimals(1); self.sym_in.setSingleStep(0.1); self.sym_in.setValue(50.0); self.sym_in.setSuffix(" %")
        
        self.btn_apply_gen = QPushButton("Siųsti parametrus")
        self.btn_apply_gen.setStyleSheet(style_purple)
        
        ch_toggle_layout = QHBoxLayout()
        self.btn_gen_ch1 = QPushButton("CH1 Išėjimas"); self.btn_gen_ch1.setCheckable(True); self.btn_gen_ch1.setStyleSheet(style_toggle)
        self.btn_gen_ch2 = QPushButton("CH2 Išėjimas"); self.btn_gen_ch2.setCheckable(True); self.btn_gen_ch2.setStyleSheet(style_toggle)
        ch_toggle_layout.addWidget(self.btn_gen_ch1); ch_toggle_layout.addWidget(self.btn_gen_ch2)

        gen_layout.addRow("Konfigūruoti:", self.gen_ch_select)
        gen_layout.addRow("Tipas:", self.wave_type)
        gen_layout.addRow("Dažnis:", f_widget)
        gen_layout.addRow("Amplitudė:", self.amp_in)
        gen_layout.addRow("Poslinkis:", self.offset_in)
        gen_layout.addRow("Fazė:", self.phase_in)
        gen_layout.addRow("Darbo ciklas (Duty):", self.duty_in)
        gen_layout.addRow("Simetrija (Sym):", self.sym_in)
        gen_layout.addRow(self.btn_apply_gen)
        gen_layout.addRow(ch_toggle_layout)
        self.ctrl_tabs.addTab(gen_tab, "Gen")

        # 2. Oscilografas
        osc_tab = QWidget(); osc_layout = QVBoxLayout(osc_tab)
        osc_ch_grid = QGridLayout()
        self.btn_osc_ch1 = QPushButton("CH1"); self.btn_osc_ch1.setCheckable(True); self.btn_osc_ch1.setStyleSheet(style_toggle)
        self.btn_osc_ch2 = QPushButton("CH2"); self.btn_osc_ch2.setCheckable(True); self.btn_osc_ch2.setStyleSheet(style_toggle)
        self.btn_osc_ch3 = QPushButton("CH3"); self.btn_osc_ch3.setCheckable(True); self.btn_osc_ch3.setStyleSheet(style_toggle)
        self.btn_osc_ch4 = QPushButton("CH4"); self.btn_osc_ch4.setCheckable(True); self.btn_osc_ch4.setStyleSheet(style_toggle)
        osc_ch_grid.addWidget(self.btn_osc_ch1, 0, 0); osc_ch_grid.addWidget(self.btn_osc_ch2, 0, 1)
        osc_ch_grid.addWidget(self.btn_osc_ch3, 1, 0); osc_ch_grid.addWidget(self.btn_osc_ch4, 1, 1)
        
        ctrl_box = QHBoxLayout()
        self.btn_auto = QPushButton("Auto-Scale"); self.btn_run = QPushButton("Run / Stop"); self.btn_run.setCheckable(True)
        self.btn_auto.setStyleSheet(style_blue); self.btn_run.setStyleSheet(style_toggle)
        ctrl_box.addWidget(self.btn_auto); ctrl_box.addWidget(self.btn_run)

        meas_group = QGroupBox("Aparatūriniai matavimai")
        meas_layout = QVBoxLayout(meas_group)
        ch_sel_layout = QHBoxLayout()
        ch_sel_layout.addWidget(QLabel("Matuoti iš:"))
        self.combo_meas_ch = QComboBox(); self.combo_meas_ch.addItems(["CH1", "CH2", "CH3", "CH4"])
        ch_sel_layout.addWidget(self.combo_meas_ch)
        self.btn_meas_all = QPushButton("Atnaujinti parametrus")
        self.btn_meas_all.setStyleSheet(style_blue)
        ch_sel_layout.addWidget(self.btn_meas_all)
        meas_layout.addLayout(ch_sel_layout)

        self.table_meas = QTableWidget(0, 2)
        self.table_meas.setHorizontalHeaderLabels(["Parametras", "Reikšmė"])
        self.table_meas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_meas.verticalHeader().setVisible(False)
        meas_layout.addWidget(self.table_meas)

        osc_layout.addWidget(QLabel("<b>Kanalų rodymas:</b>"))
        osc_layout.addLayout(osc_ch_grid); osc_layout.addLayout(ctrl_box)
        osc_layout.addWidget(meas_group)
        self.ctrl_tabs.addTab(osc_tab, "Osc")

        # 3. Multimetrai
        multi_tab = QWidget(); multi_layout = QVBoxLayout(multi_tab)
        
        self.tti_dc_style = "font-size: 32pt; font-family: 'Consolas'; color: #00FF00; background: black; border-radius: 5px; padding: 10px;"
        self.tti_ac_style = "font-size: 32pt; font-family: 'Consolas'; color: #FFA500; background: black; border-radius: 5px; padding: 10px;"
        
        tti_group = QGroupBox("TTi 1604 Nuotolinis Valdymas")
        tti_main_layout = QVBoxLayout(tti_group)

        self.lbl_tti_val = QLabel("----")
        self.lbl_tti_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tti_val.setStyleSheet(self.tti_dc_style)

        tti_main_layout.addWidget(self.lbl_tti_val)

        tti_ctrl_grid = QGridLayout()
        
        self.btn_tti_operate = QPushButton("Operate"); self.btn_tti_operate.setStyleSheet(style_purple)
        self.btn_tti_auto = QPushButton("Auto/Man"); self.btn_tti_auto.setStyleSheet(style_purple)
        self.btn_tti_up = QPushButton("Up ▲"); self.btn_tti_up.setStyleSheet(style_purple)
        self.btn_tti_down = QPushButton("Down ▼"); self.btn_tti_down.setStyleSheet(style_purple)

        self.btn_tti_v = QPushButton("V"); self.btn_tti_v.setStyleSheet(style_gray)
        self.btn_tti_a = QPushButton("A"); self.btn_tti_a.setStyleSheet(style_gray)
        self.btn_tti_ma = QPushButton("mA"); self.btn_tti_ma.setStyleSheet(style_gray)
        self.btn_tti_mv = QPushButton("mV"); self.btn_tti_mv.setStyleSheet(style_gray)
        self.btn_tti_dc = QPushButton("DC"); self.btn_tti_dc.setStyleSheet(style_gray)
        self.btn_tti_ac = QPushButton("AC"); self.btn_tti_ac.setStyleSheet(style_gray)
        self.btn_tti_ohm = QPushButton("Ohm"); self.btn_tti_ohm.setStyleSheet(style_gray)
        self.btn_tti_hz = QPushButton("Hz"); self.btn_tti_hz.setStyleSheet(style_gray)

        self.btn_tti_diode = QPushButton("Diode"); self.btn_tti_diode.setStyleSheet(style_indigo)
        self.btn_tti_minmax = QPushButton("Min-Max"); self.btn_tti_minmax.setStyleSheet(style_indigo)
        self.btn_tti_hold = QPushButton("Hold"); self.btn_tti_hold.setStyleSheet(style_indigo)
        self.btn_tti_thold = QPushButton("T-Hold"); self.btn_tti_thold.setStyleSheet(style_indigo)
        self.btn_tti_null = QPushButton("Null"); self.btn_tti_null.setStyleSheet(style_indigo)
        self.btn_tti_reset = QPushButton("Reset"); self.btn_tti_reset.setStyleSheet(style_indigo)
        self.btn_tti_cont = QPushButton("Cont"); self.btn_tti_cont.setStyleSheet(style_indigo)
        self.btn_tti_review = QPushButton("Review"); self.btn_tti_review.setStyleSheet(style_indigo)

        self.btn_tti_refresh = QPushButton("NUSKAITYTI EKRANĄ")
        self.btn_tti_refresh.setStyleSheet(style_blue)

        tti_ctrl_grid.addWidget(self.btn_tti_operate, 0, 0)
        tti_ctrl_grid.addWidget(self.btn_tti_auto, 0, 1)
        tti_ctrl_grid.addWidget(self.btn_tti_up, 0, 2)
        tti_ctrl_grid.addWidget(self.btn_tti_down, 0, 3)

        tti_ctrl_grid.addWidget(self.btn_tti_v, 1, 0)
        tti_ctrl_grid.addWidget(self.btn_tti_a, 1, 1)
        tti_ctrl_grid.addWidget(self.btn_tti_ma, 1, 2)
        tti_ctrl_grid.addWidget(self.btn_tti_mv, 1, 3)

        tti_ctrl_grid.addWidget(self.btn_tti_diode, 2, 0)
        tti_ctrl_grid.addWidget(self.btn_tti_minmax, 2, 1)
        tti_ctrl_grid.addWidget(self.btn_tti_hold, 2, 2)
        tti_ctrl_grid.addWidget(self.btn_tti_thold, 2, 3)

        tti_ctrl_grid.addWidget(self.btn_tti_dc, 3, 0)
        tti_ctrl_grid.addWidget(self.btn_tti_ac, 3, 1)
        tti_ctrl_grid.addWidget(self.btn_tti_ohm, 3, 2)
        tti_ctrl_grid.addWidget(self.btn_tti_hz, 3, 3)

        tti_ctrl_grid.addWidget(self.btn_tti_null, 4, 0)
        tti_ctrl_grid.addWidget(self.btn_tti_reset, 4, 1)
        tti_ctrl_grid.addWidget(self.btn_tti_cont, 4, 2)
        tti_ctrl_grid.addWidget(self.btn_tti_review, 4, 3)

        tti_ctrl_grid.addWidget(self.btn_tti_refresh, 5, 0, 1, 4)

        tti_main_layout.addLayout(tti_ctrl_grid)
        multi_layout.addWidget(tti_group)
        
        esc_group = QGroupBox("Escort 3136A Valdymas")
        esc_layout = QVBoxLayout(esc_group)
        
        self.lbl_esc_val = QLabel("----")
        self.lbl_esc_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_esc_val.setStyleSheet(self.tti_dc_style) 
        
        self.btn_esc_read = QPushButton("NUSKAITYTI EKRANĄ")
        self.btn_esc_read.setStyleSheet(style_blue)
        
        esc_layout.addWidget(self.lbl_esc_val)
        esc_layout.addWidget(self.btn_esc_read)

        multi_layout.addWidget(esc_group); multi_layout.addStretch()
        self.ctrl_tabs.addTab(multi_tab, "Multi")

        # 4. Bode Plot
        bode_tab = QWidget(); bode_layout = QFormLayout(bode_tab)
        self.bode_start_f = QDoubleSpinBox(); self.bode_start_f.setRange(1, 1e8); self.bode_start_f.setValue(10); self.bode_start_f.setSuffix(" Hz")
        self.bode_stop_f = QDoubleSpinBox(); self.bode_stop_f.setRange(10, 1e8); self.bode_stop_f.setValue(10000); self.bode_stop_f.setSuffix(" Hz")
        self.bode_points = QSpinBox(); self.bode_points.setRange(2, 10000); self.bode_points.setValue(50)
        self.bode_amp = QDoubleSpinBox(); self.bode_amp.setRange(0.01, 20.0); self.bode_amp.setValue(1.0); self.bode_amp.setSuffix(" Vpp")
        
        self.bode_gen_ch = QComboBox(); self.bode_gen_ch.addItems(["CH1", "CH2"])
        self.bode_device = QComboBox(); self.bode_device.addItems(["Rigol MSO (Vpp)", "TTi 1604 (V)", "Escort 3136A (V)"])
        self.bode_osc_ch = QComboBox(); self.bode_osc_ch.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.lbl_bode_osc_ch = QLabel("Osc. Kanalas:")

        self.btn_start_bode = QPushButton("Pradėti skenavimą"); self.btn_stop_bode = QPushButton("Stabdyti")
        self.btn_start_bode.setStyleSheet(style_green); self.btn_stop_bode.setStyleSheet(style_red)
        
        bode_layout.addRow("Pradinis f:", self.bode_start_f)
        bode_layout.addRow("Galinis f:", self.bode_stop_f)
        bode_layout.addRow("Taškų sk.:", self.bode_points)
        bode_layout.addRow("Vin Amp:", self.bode_amp)
        bode_layout.addRow("Gen. Kanalas:", self.bode_gen_ch)
        bode_layout.addRow("Matuoklis:", self.bode_device)
        bode_layout.addRow(self.lbl_bode_osc_ch, self.bode_osc_ch)
        bode_layout.addRow(self.btn_start_bode, self.btn_stop_bode)
        self.bode_progress = QProgressBar(); self.bode_progress.setValue(0)
        bode_layout.addRow(self.bode_progress)
        self.ctrl_tabs.addTab(bode_tab, "Bode")

        # 5. Logger
        log_tab = QWidget(); log_layout = QFormLayout(log_tab)
        self.log_device = QComboBox(); self.log_device.addItems(["TTi 1604", "Escort 3136A"])
        self.log_mode = QComboBox(); self.log_mode.addItems(["Įtampa (V)", "Srovė (A)"])
        self.log_interval = QDoubleSpinBox(); self.log_interval.setRange(0.5, 3600.0); self.log_interval.setValue(1.0)
        self.log_duration = QSpinBox(); self.log_duration.setRange(0, 10000); self.log_duration.setValue(0)
        self.btn_start_log = QPushButton("Pradėti registravimą"); self.btn_stop_log = QPushButton("Stabdyti")
        self.btn_start_log.setStyleSheet(style_green); self.btn_stop_log.setStyleSheet(style_red)
        self.lbl_log_current = QLabel("Reikšmė: -"); self.lbl_log_current.setStyleSheet("font-weight: bold; color: #FFC107;")
        log_layout.addRow("Prietaisas:", self.log_device); log_layout.addRow("Matavimas:", self.log_mode)
        log_layout.addRow("Interv. (s):", self.log_interval); log_layout.addRow("Trukmė (m):", self.log_duration)
        log_layout.addRow(self.btn_start_log, self.btn_stop_log); log_layout.addRow(self.lbl_log_current)
        self.ctrl_tabs.addTab(log_tab, "Logger")

        # 6. FFT
        fft_tab = QWidget(); fft_layout = QVBoxLayout(fft_tab)
        self.btn_calc_fft = QPushButton("Nuskaityti ir skaičiuoti FFT")
        self.btn_calc_fft.setStyleSheet(style_purple)
        self.lbl_fft_peak = QLabel("Pikas: - Hz"); self.lbl_fft_peak.setStyleSheet("font-weight: bold; color: #00BCD4;")
        fft_layout.addWidget(self.btn_calc_fft); fft_layout.addWidget(self.lbl_fft_peak); fft_layout.addStretch()
        self.ctrl_tabs.addTab(fft_tab, "FFT")

        left_layout.addWidget(self.ctrl_tabs)

        self.log_console = QTextEdit(); self.log_console.setReadOnly(True); self.log_console.setMaximumHeight(150)
        self.log_console.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 11px;")
        left_layout.addWidget(QLabel("<b>Žurnalas:</b>")); left_layout.addWidget(self.log_console)

        scroll_area.setWidget(container)
        self.splitter.addWidget(scroll_area)

        self.graph_tabs = QTabWidget()
        
        osc_graph_tab = QWidget(); osc_graph_layout = QVBoxLayout(osc_graph_tab)
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setLabel('left', 'Įtampa', units='V'); self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        self.graph_widget.showGrid(x=True, y=True)
        stream_ctrl = QHBoxLayout()
        self.btn_start_stream = QPushButton("Pradėti gyvą rodymą"); self.btn_stop_stream = QPushButton("Stabdyti"); self.btn_export = QPushButton("Eksportuoti CSV")
        self.btn_start_stream.setStyleSheet(style_green)
        self.btn_stop_stream.setStyleSheet(style_red)
        self.btn_export.setStyleSheet(style_indigo)
        stream_ctrl.addWidget(self.btn_start_stream); stream_ctrl.addWidget(self.btn_stop_stream); stream_ctrl.addWidget(self.btn_export)
        osc_graph_layout.addWidget(self.graph_widget); osc_graph_layout.addLayout(stream_ctrl)

        bode_graph_tab = QWidget(); bode_graph_layout = QVBoxLayout(bode_graph_tab)
        self.bode_graph = pg.PlotWidget()
        self.bode_graph.setLabel('left', 'Stiprinimas', units='dB'); self.bode_graph.setLabel('bottom', 'Dažnis', units='Hz (Log)')
        self.bode_graph.setLogMode(x=True, y=False); self.bode_graph.showGrid(x=True, y=True)
        self.btn_export_bode = QPushButton("Eksportuoti Bode CSV"); self.btn_export_bode.setStyleSheet(style_indigo)
        bode_graph_layout.addWidget(self.bode_graph); bode_graph_layout.addWidget(self.btn_export_bode)

        log_graph_tab = QWidget(); log_graph_layout = QVBoxLayout(log_graph_tab)
        self.log_graph = pg.PlotWidget()
        self.log_graph.setLabel('left', 'Reikšmė'); self.log_graph.setLabel('bottom', 'Laikas', units='s'); self.log_graph.showGrid(x=True, y=True)
        log_graph_layout.addWidget(self.log_graph)

        fft_graph_tab = QWidget(); fft_graph_layout = QVBoxLayout(fft_graph_tab)
        self.fft_graph = pg.PlotWidget()
        self.fft_graph.setLabel('left', 'Amplitudė', units='V'); self.fft_graph.setLabel('bottom', 'Dažnis', units='Hz'); self.fft_graph.showGrid(x=True, y=True)
        fft_graph_layout.addWidget(self.fft_graph)

        self.graph_tabs.addTab(osc_graph_tab, "Gyva Oscilograma")
        self.graph_tabs.addTab(bode_graph_tab, "Bode Dažninė Charakteristika")
        self.graph_tabs.addTab(log_graph_tab, "Ilgalaikis Registravimas")
        self.graph_tabs.addTab(fft_graph_tab, "Spektrinė Analizė (FFT)")
        
        self.splitter.addWidget(self.graph_tabs)
        self.splitter.setSizes([450, 950])