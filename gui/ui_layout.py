import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QDoubleSpinBox, QFormLayout, QComboBox, 
                             QTextEdit, QTabWidget, QGroupBox, QGridLayout, 
                             QProgressBar, QSpinBox, QLineEdit, QSplitter, 
                             QHeaderView, QTableWidget, QAbstractItemView)
from PyQt6.QtCore import Qt
from gui.theme import *

class Ui_MainWindow:
    def setup_ui(self, MainWindow):
        MainWindow.setWindowTitle("Automatizuota Matavimų Sistema")
        MainWindow.resize(1450, 950)

        central_widget = QWidget()
        MainWindow.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- KAIRĖ: Valdymas ---
        left_container = QWidget()
        left_v_layout = QVBoxLayout(left_container)
        left_v_layout.setContentsMargins(0, 0, 0, 0)
        left_v_layout.setSpacing(5)

        # 1. Bendra Informacija (Ryšys)
        self.conn_group = QGroupBox("Bendra Informacija (Ryšys)")
        conn_layout = QFormLayout(self.conn_group)
        conn_layout.setContentsMargins(5, 10, 5, 5)
        conn_layout.setSpacing(5)
        
        self.btn_scan = QPushButton("Skenuoti VISA ir COM")
        self.btn_scan.setStyleSheet(STYLE_PRIMARY)
        self.combo_gen = QComboBox()
        self.combo_osc = QComboBox()
        self.combo_tti = QComboBox()
        self.combo_escort = QComboBox()
        self.input_serial = QLineEdit()
        self.btn_generate_pdf = QPushButton("Generuoti PDF")
        self.btn_generate_pdf.setStyleSheet(STYLE_EXPORT)
        
        conn_layout.addRow(self.btn_scan)
        conn_layout.addRow("Generatorius:", self.combo_gen)
        conn_layout.addRow("Oscilografas:", self.combo_osc)
        conn_layout.addRow("TTi 1604:", self.combo_tti)
        conn_layout.addRow("Escort 3136A:", self.combo_escort)
        conn_layout.addRow("Serijos Nr.:", self.input_serial)
        conn_layout.addRow(self.btn_generate_pdf)
        left_v_layout.addWidget(self.conn_group)

        # 2. Instrumentų Tabai
        self.left_tabs = QTabWidget()

        # [TAB] Generatorius
        tab_gen = QWidget(); gen_l = QVBoxLayout(tab_gen); gen_l.setContentsMargins(5, 5, 5, 5)
        grid_g = QGridLayout(); grid_g.setSpacing(5)
        
        self.gen_ch_select = QComboBox(); self.gen_ch_select.addItems(["CH1", "CH2"])
        self.wave_type = QComboBox(); self.wave_type.addItems(["Sine", "Square", "Ramp", "Pulse", "Noise", "Arb"])
        self.combo_freq_type = QComboBox(); self.combo_freq_type.addItems(["Dažnis (Freq)", "Periodas (Period)"])
        self.freq_in = QDoubleSpinBox(); self.freq_in.setRange(0, 1e8); self.freq_in.setValue(1000)
        self.freq_unit = QComboBox(); self.freq_unit.addItems(["Hz", "kHz", "MHz"])
        
        self.f_widget = QWidget(); l_f = QHBoxLayout(self.f_widget); l_f.setContentsMargins(0,0,0,0); l_f.addWidget(self.freq_in); l_f.addWidget(self.freq_unit)

        self.combo_amp_type = QComboBox(); self.combo_amp_type.addItems(["Amplitudė/Poslinkis", "High/Low Level"])
        self.amp_in = QDoubleSpinBox(); self.amp_in.setRange(-10, 10); self.amp_in.setValue(4)
        self.offset_in = QDoubleSpinBox(); self.offset_in.setRange(-10, 10)
        self.phase_in = QDoubleSpinBox(); self.phase_in.setRange(0, 360)
        self.duty_in = QDoubleSpinBox(); self.duty_in.setRange(0.001, 99.999); self.duty_in.setValue(50)
        self.sym_in = QDoubleSpinBox(); self.sym_in.setRange(0, 100); self.sym_in.setValue(50)
        self.delay_in = QDoubleSpinBox(); self.delay_in.setRange(0, 1000); self.delay_in.setDecimals(9)
        self.stdev_in = QDoubleSpinBox(); self.stdev_in.setRange(0, 10); self.stdev_in.setDecimals(3)
        self.mean_in = QDoubleSpinBox(); self.mean_in.setRange(-10, 10); self.mean_in.setDecimals(3)

        grid_g.addWidget(QLabel("Kanalas:"), 0, 0); grid_g.addWidget(self.gen_ch_select, 0, 1)
        grid_g.addWidget(QLabel("Forma:"), 1, 0); grid_g.addWidget(self.wave_type, 1, 1)
        grid_g.addWidget(self.combo_freq_type, 2, 0); grid_g.addWidget(self.f_widget, 2, 1)
        grid_g.addWidget(self.combo_amp_type, 3, 0); grid_g.addWidget(self.amp_in, 3, 1)
        grid_g.addWidget(QLabel("Poslinkis:"), 4, 0); grid_g.addWidget(self.offset_in, 4, 1)
        grid_g.addWidget(QLabel("Fazė (°):"), 5, 0); grid_g.addWidget(self.phase_in, 5, 1)
        grid_g.addWidget(QLabel("Duty (%):"), 6, 0); grid_g.addWidget(self.duty_in, 6, 1)
        grid_g.addWidget(QLabel("Simetrija (%):"), 7, 0); grid_g.addWidget(self.sym_in, 7, 1)
        grid_g.addWidget(QLabel("Uždelsimas (s):"), 8, 0); grid_g.addWidget(self.delay_in, 8, 1)
        grid_g.addWidget(QLabel("St. Nuokrypis:"), 9, 0); grid_g.addWidget(self.stdev_in, 9, 1)
        grid_g.addWidget(QLabel("Vidurkis:"), 10, 0); grid_g.addWidget(self.mean_in, 10, 1)

        self.btn_apply_gen = QPushButton("Taikyti Parametrus"); self.btn_apply_gen.setStyleSheet(STYLE_SUCCESS)
        self.btn_eqphase = QPushButton("Sync Fazę"); self.btn_eqphase.setStyleSheet(STYLE_NORMAL)
        self.btn_gen_ch1 = QPushButton("CH1 Išvestis"); self.btn_gen_ch1.setCheckable(True); self.btn_gen_ch1.setStyleSheet(STYLE_NORMAL)
        self.btn_gen_ch2 = QPushButton("CH2 Išvestis"); self.btn_gen_ch2.setCheckable(True); self.btn_gen_ch2.setStyleSheet(STYLE_NORMAL)

        gen_l.addLayout(grid_g); gen_l.addWidget(self.btn_apply_gen); gen_l.addWidget(self.btn_eqphase)
        h_gen = QHBoxLayout(); h_gen.addWidget(self.btn_gen_ch1); h_gen.addWidget(self.btn_gen_ch2); gen_l.addLayout(h_gen)
        gen_l.addStretch()
        self.left_tabs.addTab(tab_gen, "Gen")

        # [TAB] Oscilografas
        tab_osc = QWidget(); osc_l = QVBoxLayout(tab_osc); osc_l.setContentsMargins(5, 5, 5, 5)
        self.btn_auto = QPushButton("Auto Scale"); self.btn_auto.setStyleSheet(STYLE_PRIMARY)
        self.btn_run = QPushButton("STOP (Sustabdyta)"); self.btn_run.setCheckable(True); self.btn_run.setStyleSheet(STYLE_DANGER)
        
        h_osc_ch = QHBoxLayout()
        self.btn_osc_ch1 = QPushButton("CH1"); self.btn_osc_ch1.setCheckable(True); self.btn_osc_ch1.setStyleSheet(STYLE_NORMAL)
        self.btn_osc_ch2 = QPushButton("CH2"); self.btn_osc_ch2.setCheckable(True); self.btn_osc_ch2.setStyleSheet(STYLE_NORMAL)
        self.btn_osc_ch3 = QPushButton("CH3"); self.btn_osc_ch3.setCheckable(True); self.btn_osc_ch3.setStyleSheet(STYLE_NORMAL)
        self.btn_osc_ch4 = QPushButton("CH4"); self.btn_osc_ch4.setCheckable(True); self.btn_osc_ch4.setStyleSheet(STYLE_NORMAL)
        h_osc_ch.addWidget(self.btn_osc_ch1); h_osc_ch.addWidget(self.btn_osc_ch2); h_osc_ch.addWidget(self.btn_osc_ch3); h_osc_ch.addWidget(self.btn_osc_ch4)

        self.combo_meas_ch = QComboBox(); self.combo_meas_ch.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.btn_meas_all = QPushButton("Nuskaityti Visus Parametrus"); self.btn_meas_all.setStyleSheet(STYLE_PRIMARY)
        
        self.table_meas = QTableWidget(18, 2)
        self.table_meas.setHorizontalHeaderLabels(["Parametras", "Reikšmė"])
        self.table_meas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_meas.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_meas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        
        self.btn_osc_screenshot = QPushButton("Išsaugoti Ekrano Kopiją"); self.btn_osc_screenshot.setStyleSheet(STYLE_NORMAL)
        self.btn_copy_meas = QPushButton("Kopijuoti Matavimus"); self.btn_copy_meas.setStyleSheet(STYLE_NORMAL)

        h_osc_btns = QHBoxLayout()
        h_osc_btns.addWidget(self.btn_osc_screenshot)
        h_osc_btns.addWidget(self.btn_copy_meas)

        osc_l.addWidget(self.btn_auto); osc_l.addWidget(self.btn_run); osc_l.addLayout(h_osc_ch)
        osc_l.addWidget(QLabel("Kanalas:")); osc_l.addWidget(self.combo_meas_ch); osc_l.addWidget(self.btn_meas_all)
        osc_l.addWidget(self.table_meas)
        osc_l.addLayout(h_osc_btns)
        
        self.left_tabs.addTab(tab_osc, "Osc")
        
        # [TAB] TTi 1604
        tab_tti = QWidget(); tti_l = QVBoxLayout(tab_tti); tti_l.setContentsMargins(5, 5, 5, 5)
        self.lbl_tti_val = QLabel("---"); self.lbl_tti_val.setStyleSheet(STYLE_LCD_DC)
        self.lbl_tti_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        t_grid1 = QGridLayout(); t_grid1.setSpacing(2)
        self.btn_tti_operate = QPushButton("OPERATE"); self.btn_tti_operate.setStyleSheet(STYLE_NORMAL)
        self.btn_tti_up = QPushButton("UP ▲"); self.btn_tti_up.setStyleSheet(STYLE_NORMAL)
        self.btn_tti_down = QPushButton("DOWN ▼"); self.btn_tti_down.setStyleSheet(STYLE_NORMAL)
        self.btn_tti_auto = QPushButton("AUTO"); self.btn_tti_auto.setStyleSheet(STYLE_NORMAL)
        t_grid1.addWidget(self.btn_tti_operate, 0, 0, 1, 2)
        t_grid1.addWidget(self.btn_tti_up, 1, 0); t_grid1.addWidget(self.btn_tti_down, 1, 1); t_grid1.addWidget(self.btn_tti_auto, 2, 0, 1, 2)

        t_grid2 = QGridLayout(); t_grid2.setSpacing(2)
        self.btn_tti_v = QPushButton("V"); self.btn_tti_a = QPushButton("A"); self.btn_tti_ma = QPushButton("mA"); self.btn_tti_mv = QPushButton("mV")
        self.btn_tti_dc = QPushButton("DC"); self.btn_tti_ac = QPushButton("AC"); self.btn_tti_ohm = QPushButton("OHM"); self.btn_tti_hz = QPushButton("Hz")
        
        self.btn_tti_diode = QPushButton("Diode"); self.btn_tti_cont = QPushButton("Continuity")
        self.btn_tti_null = QPushButton("NULL (Set Zero)"); self.btn_tti_null.setCheckable(True)
        self.btn_tti_reset = QPushButton("RESET")

        for btn in [self.btn_tti_v, self.btn_tti_a, self.btn_tti_ma, self.btn_tti_mv, self.btn_tti_dc, self.btn_tti_ac, self.btn_tti_ohm, self.btn_tti_hz, self.btn_tti_diode, self.btn_tti_cont, self.btn_tti_null, self.btn_tti_reset]:
            btn.setStyleSheet(STYLE_NORMAL)
            
        t_grid2.addWidget(self.btn_tti_v, 0, 0); t_grid2.addWidget(self.btn_tti_a, 0, 1); t_grid2.addWidget(self.btn_tti_ma, 0, 2); t_grid2.addWidget(self.btn_tti_mv, 0, 3)
        t_grid2.addWidget(self.btn_tti_dc, 1, 0); t_grid2.addWidget(self.btn_tti_ac, 1, 1); t_grid2.addWidget(self.btn_tti_ohm, 1, 2); t_grid2.addWidget(self.btn_tti_hz, 1, 3)
        t_grid2.addWidget(self.btn_tti_diode, 2, 0); t_grid2.addWidget(self.btn_tti_cont, 2, 1); t_grid2.addWidget(self.btn_tti_null, 2, 2); t_grid2.addWidget(self.btn_tti_reset, 2, 3)

        self.btn_tti_refresh = QPushButton("Nuskaityti TTi"); self.btn_tti_refresh.setStyleSheet(STYLE_PRIMARY)
        tti_l.addWidget(self.lbl_tti_val); tti_l.addLayout(t_grid1); tti_l.addLayout(t_grid2); tti_l.addWidget(self.btn_tti_refresh); tti_l.addStretch()
        self.left_tabs.addTab(tab_tti, "TTi")

        # [TAB] Escort 3136A
        tab_esc = QWidget(); esc_l = QVBoxLayout(tab_esc); esc_l.setContentsMargins(5, 5, 5, 5)
        self.lbl_esc_val = QLabel("---"); self.lbl_esc_val.setStyleSheet(STYLE_LCD_DC)
        self.lbl_esc_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        e_grid = QGridLayout(); e_grid.setSpacing(2)
        self.btn_esc_vdc = QPushButton("V DC"); self.btn_esc_vac = QPushButton("V AC"); self.btn_esc_ohm = QPushButton("Ω")
        self.btn_esc_adc = QPushButton("A DC"); self.btn_esc_aac = QPushButton("A AC"); self.btn_esc_diode = QPushButton("Diode")
        self.btn_esc_hz = QPushButton("Hz")
        for btn in [self.btn_esc_vdc, self.btn_esc_vac, self.btn_esc_ohm, self.btn_esc_adc, self.btn_esc_aac, self.btn_esc_diode, self.btn_esc_hz]:
            btn.setStyleSheet(STYLE_NORMAL)
        e_grid.addWidget(self.btn_esc_vdc, 0, 0); e_grid.addWidget(self.btn_esc_vac, 0, 1); e_grid.addWidget(self.btn_esc_ohm, 0, 2)
        e_grid.addWidget(self.btn_esc_adc, 1, 0); e_grid.addWidget(self.btn_esc_aac, 1, 1); e_grid.addWidget(self.btn_esc_diode, 1, 2)
        e_grid.addWidget(self.btn_esc_hz, 2, 0)
        
        self.btn_esc_read_all = QPushButton("Nuskaityti Escort"); self.btn_esc_read_all.setStyleSheet(STYLE_PRIMARY)
        esc_l.addWidget(self.lbl_esc_val); esc_l.addLayout(e_grid); esc_l.addWidget(self.btn_esc_read_all); esc_l.addStretch()
        self.left_tabs.addTab(tab_esc, "Escort")

        # [TAB] Bode
        tab_bode = QWidget(); bode_l = QGridLayout(tab_bode); bode_l.setContentsMargins(5, 5, 5, 5); bode_l.setSpacing(5)
        self.bode_start_f = QSpinBox(); self.bode_start_f.setRange(1, 1000000); self.bode_start_f.setValue(100)
        self.bode_stop_f = QSpinBox(); self.bode_stop_f.setRange(10, 10000000); self.bode_stop_f.setValue(100000)
        self.bode_points = QSpinBox(); self.bode_points.setRange(5, 500); self.bode_points.setValue(50)
        self.bode_amp = QDoubleSpinBox(); self.bode_amp.setRange(0.1, 10); self.bode_amp.setValue(2.0)
        self.bode_device = QComboBox(); self.bode_device.addItems(["Rigol MSO", "TTi 1604", "Escort 3136A"])
        self.bode_gen_ch = QComboBox(); self.bode_gen_ch.addItems(["CH1", "CH2"])
        self.bode_osc_ch = QComboBox(); self.bode_osc_ch.addItems(["CH1", "CH2", "CH3", "CH4"])
        
        bode_l.addWidget(QLabel("Pradinis (Hz):"), 0, 0); bode_l.addWidget(self.bode_start_f, 0, 1)
        bode_l.addWidget(QLabel("Galinis (Hz):"), 1, 0); bode_l.addWidget(self.bode_stop_f, 1, 1)
        bode_l.addWidget(QLabel("Taškų sk.:"), 2, 0); bode_l.addWidget(self.bode_points, 2, 1)
        bode_l.addWidget(QLabel("Amplitudė (V):"), 3, 0); bode_l.addWidget(self.bode_amp, 3, 1)
        bode_l.addWidget(QLabel("Matuoklis:"), 4, 0); bode_l.addWidget(self.bode_device, 4, 1)
        bode_l.addWidget(QLabel("Gen. Kanalas:"), 5, 0); bode_l.addWidget(self.bode_gen_ch, 5, 1)
        self.lbl_bode_osc_ch = QLabel("Osc. Kanalas:")
        bode_l.addWidget(self.lbl_bode_osc_ch, 6, 0); bode_l.addWidget(self.bode_osc_ch, 6, 1)

        self.btn_start_bode = QPushButton("Pradėti Bode"); self.btn_start_bode.setStyleSheet(STYLE_SUCCESS)
        self.btn_stop_bode = QPushButton("Stabdyti"); self.btn_stop_bode.setStyleSheet(STYLE_DANGER)
        self.bode_progress = QProgressBar(); self.bode_progress.setValue(0)
        bode_l.addWidget(self.btn_start_bode, 7, 0, 1, 2); bode_l.addWidget(self.btn_stop_bode, 8, 0, 1, 2)
        bode_l.addWidget(self.bode_progress, 9, 0, 1, 2); bode_l.setRowStretch(10, 1)
        self.left_tabs.addTab(tab_bode, "Bode")

        # [TAB] Logger
        tab_log = QWidget(); log_l = QGridLayout(tab_log); log_l.setContentsMargins(5, 5, 5, 5); log_l.setSpacing(5)
        self.log_device = QComboBox(); self.log_device.addItems(["TTi 1604", "Escort 3136A"])
        self.log_mode = QComboBox(); self.log_mode.addItems(["V DC", "V AC", "A DC", "A AC", "mA DC", "mA AC", "OHM", "Hz"])
        self.log_interval = QSpinBox(); self.log_interval.setRange(100, 60000); self.log_interval.setValue(1000)
        self.log_duration = QSpinBox(); self.log_duration.setRange(0, 1440); self.log_duration.setValue(0)
        
        log_l.addWidget(QLabel("Prietaisas:"), 0, 0); log_l.addWidget(self.log_device, 0, 1)
        log_l.addWidget(QLabel("Režimas:"), 1, 0); log_l.addWidget(self.log_mode, 1, 1)
        log_l.addWidget(QLabel("Intervalas (ms):"), 2, 0); log_l.addWidget(self.log_interval, 2, 1)
        log_l.addWidget(QLabel("Trukmė (min):"), 3, 0); log_l.addWidget(self.log_duration, 3, 1)

        self.lbl_log_current = QLabel("Dabartinė: ---")
        self.btn_start_log = QPushButton("Pradėti Registravimą"); self.btn_start_log.setStyleSheet(STYLE_SUCCESS)
        self.btn_stop_log = QPushButton("Stabdyti"); self.btn_stop_log.setStyleSheet(STYLE_DANGER)
        log_l.addWidget(self.lbl_log_current, 4, 0, 1, 2); log_l.addWidget(self.btn_start_log, 5, 0, 1, 2)
        log_l.addWidget(self.btn_stop_log, 6, 0, 1, 2); log_l.setRowStretch(7, 1)
        self.left_tabs.addTab(tab_log, "Logger")

        left_v_layout.addWidget(self.left_tabs)
        self.splitter.addWidget(left_container)

        # --- DEŠINĖ: Grafikai ir Žurnalas ---
        right_container = QWidget(); right_v_layout = QVBoxLayout(right_container)
        right_v_layout.setContentsMargins(0, 0, 0, 0); right_v_layout.setSpacing(5)
        
        self.graph_tabs = QTabWidget()
        
        # Oscilograma
        tab_g_osc = QWidget(); l_g_osc = QVBoxLayout(tab_g_osc); l_g_osc.setContentsMargins(0, 0, 0, 0)
        self.graph_widget = pg.PlotWidget(); self.graph_widget.showGrid(x=True, y=True)
        self.graph_widget.setLabel('left', 'Įtampa', units='V'); self.graph_widget.setLabel('bottom', 'Laikas', units='s')
        
        h_ctrl_osc = QHBoxLayout()
        self.btn_stream = QPushButton("START Atvaizdavimą")
        self.btn_stream.setCheckable(True)
        self.btn_stream.setStyleSheet(STYLE_DANGER)
        self.btn_calc_fft = QPushButton("Skaičiuoti FFT"); self.btn_calc_fft.setStyleSheet(STYLE_PRIMARY)
        self.btn_export = QPushButton("Eksportuoti CSV"); self.btn_export.setStyleSheet(STYLE_EXPORT)
        
        h_ctrl_osc.addWidget(self.btn_stream)
        h_ctrl_osc.addWidget(self.btn_calc_fft)
        h_ctrl_osc.addWidget(self.btn_export)
        
        l_g_osc.addWidget(self.graph_widget); l_g_osc.addLayout(h_ctrl_osc)
        self.graph_tabs.addTab(tab_g_osc, "Oscilograma")

        # Bode
        tab_g_bode = QWidget(); l_g_bode = QVBoxLayout(tab_g_bode); l_g_bode.setContentsMargins(0, 0, 0, 0)
        self.bode_graph = pg.PlotWidget(); self.bode_graph.showGrid(x=True, y=True); self.bode_graph.setLogMode(x=True, y=False)
        self.bode_graph.setLabel('left', 'Stiprinimas', units='dB'); self.bode_graph.setLabel('bottom', 'Dažnis', units='Hz')
        self.btn_export_bode = QPushButton("Eksportuoti Bode"); self.btn_export_bode.setStyleSheet(STYLE_EXPORT)
        l_g_bode.addWidget(self.bode_graph); l_g_bode.addWidget(self.btn_export_bode)
        self.graph_tabs.addTab(tab_g_bode, "Bode Analizė")

        # Logger
        tab_g_log = QWidget(); l_g_log = QVBoxLayout(tab_g_log); l_g_log.setContentsMargins(0, 0, 0, 0)
        self.log_graph = pg.PlotWidget(); self.log_graph.showGrid(x=True, y=True)
        self.log_graph.setLabel('left', 'Reikšmė'); self.log_graph.setLabel('bottom', 'Laikas', units='s')
        l_g_log.addWidget(self.log_graph)
        self.graph_tabs.addTab(tab_g_log, "Ilgalaikis Registravimas")

        # FFT
        tab_g_fft = QWidget(); l_g_fft = QVBoxLayout(tab_g_fft); l_g_fft.setContentsMargins(0, 0, 0, 0)
        self.fft_graph = pg.PlotWidget(); self.fft_graph.showGrid(x=True, y=True)
        self.fft_graph.setLabel('left', 'Amplitudė', units='V'); self.fft_graph.setLabel('bottom', 'Dažnis', units='Hz')
        self.lbl_fft_peak = QLabel("Pikas: ---")
        self.lbl_fft_peak.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        l_g_fft.addWidget(self.fft_graph); l_g_fft.addWidget(self.lbl_fft_peak)
        self.graph_tabs.addTab(tab_g_fft, "FFT")

        # Žurnalas
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(120)
        self.log_console.setStyleSheet("border: 1px solid #3c3c3c; background: #0f0f0f; color: #fff;")
        self.log_console.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        self.btn_save_log = QPushButton("Išsaugoti Žurnalą")
        self.btn_save_log.setStyleSheet(STYLE_NORMAL)

        right_v_layout.addWidget(self.graph_tabs)
        right_v_layout.addWidget(QLabel("Sistemos Žurnalas:"))
        right_v_layout.addWidget(self.log_console)
        right_v_layout.addWidget(self.btn_save_log)

        self.splitter.addWidget(right_container)
        self.splitter.setSizes([450, 1000])