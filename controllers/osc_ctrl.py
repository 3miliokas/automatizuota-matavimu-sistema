import numpy as np
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QApplication
from PyQt6.QtCore import QTimer
from gui.theme import STYLE_SUCCESS, STYLE_DANGER

class OscController:
    """
    Rigol MSO oscilografo valdymo ir signalų analizės valdiklis.
    Apdoroja realaus laiko oscilogramų atvaizdavimą, parametrų nuskaitymą,
    greitąją Furjė transformaciją (FFT) bei ekrano kopijų išsaugojimą.
    Užtikrina dvikryptę sinchronizaciją su fizinio prietaiso būsena.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        
        # Laikmatis skirtas realaus laiko signalų atvaizdavimo (stream) ciklui
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_plot)

        # UI elementų signalų susiejimas
        self.ui.combo_osc.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_auto.clicked.connect(self.trigger_autoscale)
        self.ui.btn_run.toggled.connect(self.toggle_run_stop)
        
        # Kanalų rodymo mygtukų lambda funkcijos užtikrina tiek GUI, tiek aparatūros būsenos atnaujinimą
        self.ui.btn_osc_ch1.toggled.connect(lambda s: (self.set_display(s, 1), self.main.update_toggle_button_style(self.ui.btn_osc_ch1, s), self.main.curves[1].setVisible(s)))
        self.ui.btn_osc_ch2.toggled.connect(lambda s: (self.set_display(s, 2), self.main.update_toggle_button_style(self.ui.btn_osc_ch2, s), self.main.curves[2].setVisible(s)))
        self.ui.btn_osc_ch3.toggled.connect(lambda s: (self.set_display(s, 3), self.main.update_toggle_button_style(self.ui.btn_osc_ch3, s), self.main.curves[3].setVisible(s)))
        self.ui.btn_osc_ch4.toggled.connect(lambda s: (self.set_display(s, 4), self.main.update_toggle_button_style(self.ui.btn_osc_ch4, s), self.main.curves[4].setVisible(s)))
        
        self.ui.btn_meas_all.clicked.connect(self.fetch_measurements)
        self.ui.btn_osc_screenshot.clicked.connect(self.save_screenshot)
        self.ui.btn_copy_meas.clicked.connect(self.copy_measurements)
        self.ui.btn_stream.toggled.connect(self.toggle_stream)
        self.ui.btn_calc_fft.clicked.connect(self.calculate_fft)

    def _on_changed(self):
        """Apdoroja oscilografo adreso pasikeitimą išskleidžiamajame sąraše."""
        addr = self.ui.combo_osc.currentData()
        if addr: 
            self.mgr.connect_osc(addr)
        else:
            with self.mgr.lock:
                if self.mgr.osc: 
                    self.mgr.osc.close()
                    self.mgr.osc = None

    def trigger_autoscale(self):
        """Inicijuoja oscilografo automatinio mastelio pritaikymą (Auto Scale)."""
        if not self.mgr.osc: return
        with self.mgr.lock: 
            self.mgr.osc.auto_scale()
        self.ui.graph_widget.enableAutoRange()

    def toggle_run_stop(self, state):
        """Keičia oscilografo trigerio (RUN/STOP) būseną."""
        if not self.mgr.osc: return
        with self.mgr.lock: 
            self.mgr.osc.run() if state else self.mgr.osc.stop()
        self.main.update_run_stop_btn(self.ui.btn_run, state)

    def set_display(self, state, channel):
        """Įjungia arba išjungia kanalo atvaizdavimą fiziniame oscilografo ekrane."""
        if not self.mgr.osc: return
        with self.mgr.lock: 
            self.mgr.osc.set_channel_display(state, channel)

    def fetch_measurements(self):
        """Inicijuoja visų parametrų matavimą pasirinktam kanalui."""
        if not self.mgr.osc: return
        self.main.show_loading("Nuskaitomi parametrai iš oscilografo...")
        QTimer.singleShot(100, self._perform_fetch)

    def _perform_fetch(self):
        """
        Nuskaito 18 skirtingų parametrų matavimus per SCPI komandas.
        Laikinai sustabdo duomenų srautą (stream), kad neperkrautų magistralės.
        """
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.stream_timer.stop()
        
        ch = self.ui.combo_meas_ch.currentIndex() + 1
        
        # SCPI komandų ir matavimo vienetų žemėlapis
        params = [("VPP", "Vpp", "V"), ("VMAX", "Vmax", "V"), ("VMIN", "Vmin", "V"), ("VAMP", "Vamp", "V"),
                  ("VTOP", "Vtop", "V"), ("VBAS", "Vbase", "V"), ("VAVG", "Vavg", "V"), ("VRMS", "Vrms", "V"),
                  ("OVER", "Overshoot", "%"), ("PRE", "Preshoot", "%"), ("FREQ", "Freq", "Hz"), ("PER", "Period", "s"),
                  ("RTIM", "Rise Time", "s"), ("FTIM", "Fall Time", "s"), ("PWID", "Pulse (+)", "s"), ("NWID", "Pulse (-)", "s"),
                  ("PDUT", "Duty (+)", "%"), ("NDUT", "Duty (-)", "%")]
                  
        with self.mgr.lock:
            for i, (cmd, name, unit) in enumerate(params):
                val = self.mgr.osc.get_measure(cmd, channel=ch)
                # Formatuojama eksponentiniu būdu; jei grąžinama klaidą indikuojanti reikšmė (1e37), rodomas brūkšnys
                val_str = f"{val:.4e} {unit}" if (val is not None and val < 1e15) else "-"
                self.ui.table_meas.setItem(i, 0, QTableWidgetItem(name))
                self.ui.table_meas.setItem(i, 1, QTableWidgetItem(val_str))
                
        self.main.hide_loading()

    def copy_measurements(self):
        """Nukopijuoja sėkmingus matavimus iš lentelės į sistemos iškarpinę."""
        text = "Parametras\tReikšmė\n"
        for i in range(self.ui.table_meas.rowCount()):
            item0 = self.ui.table_meas.item(i, 0)
            item1 = self.ui.table_meas.item(i, 1)
            # Ignoruojami tušti laukai
            if item0 and item1 and item1.text() != "-": 
                text += f"{item0.text()}\t{item1.text()}\n"
        QApplication.clipboard().setText(text)
        self.main.log_msg("Matavimų lentelė nukopijuota.")

    def save_screenshot(self):
        """Parsiunčia ir išsaugo binarinį .bmp ekrano kopijos failą tiesiai iš prietaiso."""
        if not self.mgr.osc: return
        fn, _ = QFileDialog.getSaveFileName(self.main, "Išsaugoti", "", "BMP Image (*.bmp)")
        if not fn: return
        self.main.show_loading("Traukiama ekrano kopija...")
        QTimer.singleShot(100, lambda: (
            self.mgr.lock.acquire(), 
            open(fn, 'wb').write(self.mgr.osc.get_screenshot() or b''), 
            self.mgr.lock.release(), 
            self.main.hide_loading()
        ))

    def calculate_fft(self):
        """Inicijuoja greitosios Furjė transformacijos (FFT) skaičiavimą."""
        if not self.mgr.osc: return
        self.main.show_loading("Skaičiuojama FFT...")
        QTimer.singleShot(100, self._perform_fft)

    def _perform_fft(self):
        """
        Nuskaito laiko srities (Time domain) CH1 signalo taškus,
        pritaiko numpy.fft biblioteką ir rezultatus atvaizduoja FFT grafike.
        """
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.ui.btn_stream.setChecked(False)
        self.ui.graph_tabs.setCurrentIndex(3) 
        
        with self.mgr.lock: 
            t, v = self.mgr.osc.get_waveform_data(channel=1)
            
        if len(t) > 1:
            n = len(v)
            yf = np.fft.fft(v)
            xf = np.fft.fftfreq(n, d=(t[1]-t[0]))
            half_n = n // 2
            
            # Naudojama tik pirmoji dažnių spektro pusė pagal Nyquist teoremą
            self.main.fft_x = xf[:half_n]
            self.main.fft_y = 2.0 / n * np.abs(yf[:half_n])
            self.main.fft_y[0] = 0 # Ignoruojama nuolatinė (DC) komponentė
            
            self.main.fft_line.setData(self.main.fft_x, self.main.fft_y)
            
            # Randama piko reikšmė (didžiausia amplitudė) ir jos dažnis
            peak_idx = np.argmax(self.main.fft_y)
            self.ui.lbl_fft_peak.setText(f"Pikas: {self.main.fft_x[peak_idx]:.2e} Hz ({self.main.fft_y[peak_idx]:.3f} V)")
            
        self.main.hide_loading()
        if was_streaming: self.ui.btn_stream.setChecked(True)

    def toggle_stream(self, state):
        """Įjungia arba išjungia periodinį oscilogramų naujinimą GUI lange."""
        if state:
            if not self.mgr.osc:
                self.main.log_msg("Nepasirinktas oscilografas.")
                self.ui.btn_stream.blockSignals(True)
                self.ui.btn_stream.setChecked(False)
                self.ui.btn_stream.blockSignals(False)
                return
            self.ui.graph_tabs.setCurrentIndex(0)
            self.ui.btn_stream.setText("STOP Atvaizdavimą")
            self.ui.btn_stream.setStyleSheet(STYLE_SUCCESS)
            self.stream_timer.start(2000) # Atnaujinimas kas 2 sekundes
        else:
            self.stream_timer.stop()
            self.ui.btn_stream.setText("START Atvaizdavimą")
            self.ui.btn_stream.setStyleSheet(STYLE_DANGER)

    def update_plot(self):
        """
        Ši funkcija reguliariai iškviečiama laikmačio (QTimer).
        Surenka aktyvių kanalų signalo taškus ir perbraižo (PyQtGraph) kreives.
        """
        if not self.mgr.osc: return
        
        # Tikrinama, ar resursas neužrakintas kitų fono gijų (Bode, Logger)
        if not self.mgr.lock.locked():
            with self.mgr.lock:
                # Laikinas logavimo išjungimas, siekiant neapkrauti terminalo greito ciklo metu
                old_logger = self.mgr.osc.logger
                self.mgr.osc.logger = None  
                try:
                    # Aktyvių kanalų identifikavimas iš grafinės sąsajos būsenos
                    active = [i for i, btn in enumerate([
                        self.ui.btn_osc_ch1, 
                        self.ui.btn_osc_ch2, 
                        self.ui.btn_osc_ch3, 
                        self.ui.btn_osc_ch4
                    ], 1) if btn.isChecked()]
                    
                    # Duomenų nuskaitymas ir atvaizdavimas tik aktyviems kanalams
                    for ch in range(1, 5):
                        if ch in active:
                            t, v = self.mgr.osc.get_waveform_data(channel=ch)
                            if t is not None and len(t) > 0: 
                                self.main.curves[ch].setData(t, v)
                                self.main.curves[ch].setVisible(True)
                        else:
                            self.main.curves[ch].setData([], [])
                            self.main.curves[ch].setVisible(False)
                finally: 
                    self.mgr.osc.logger = old_logger

    def sync_ui(self):
        """
        Dvikryptė sinchronizacija (Polling). 
        Atnaujina GUI kanalų rodymo būseną ir trigerio (RUN/STOP) būseną,
        jei šie parametrai buvo pakeisti pačiame prietaise.
        """
        if not self.mgr.lock.locked() and self.mgr.osc:
            with self.mgr.lock:
                old_logger = self.mgr.osc.logger
                self.mgr.osc.logger = None
                try:
                    states = [self.mgr.osc.get_channel_state(i) for i in range(1, 5)]
                    run_st = self.mgr.osc.get_run_state()
                    
                    for i, btn in enumerate([self.ui.btn_osc_ch1, self.ui.btn_osc_ch2, self.ui.btn_osc_ch3, self.ui.btn_osc_ch4]):
                        btn.blockSignals(True)
                        btn.setChecked(states[i])
                        self.main.update_toggle_button_style(btn, states[i])
                        btn.blockSignals(False)
                        self.main.curves[i+1].setVisible(states[i])
                        
                    self.ui.btn_run.blockSignals(True)
                    self.ui.btn_run.setChecked(run_st)
                    self.main.update_run_stop_btn(self.ui.btn_run, run_st)
                    self.ui.btn_run.blockSignals(False)
                except: pass
                finally: 
                    self.mgr.osc.logger = old_logger