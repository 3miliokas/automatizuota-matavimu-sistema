import numpy as np
import threading
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from gui.theme import STYLE_SUCCESS, STYLE_DANGER

# Speciali klasė signalų perdavimui iš foninės gijos į pagrindinę (GUI) giją
class OscSignals(QObject):
    meas_ready = pyqtSignal(int, dict)
    error = pyqtSignal(str)

class OscController:
    """
    Rigol MSO oscilografo valdymo ir signalų analizės valdiklis.
    Apdoroja realaus laiko oscilogramų atvaizdavimą, parametrų nuskaitymą,
    greitąją Furjė transformaciją (FFT) bei ekrano kopijų išsaugojimą.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        
        # Laikmatis skirtas realaus laiko signalų atvaizdavimo (stream) ciklui
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_plot)
        
        # Žodynas skirtas išsaugoti kiekvieno kanalo nuskaitytus matavimus atmintyje
        self.channel_data = {1: {}, 2: {}, 3: {}, 4: {}}
        
        # Sukuriamas signalų priėmėjas ir susiejamas su GUI atnaujinimo funkcijomis
        self.signals = OscSignals()
        self.signals.meas_ready.connect(self.update_table)
        self.signals.error.connect(self.on_error)

        # UI elementų signalų susiejimas
        self.ui.combo_osc.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_auto.clicked.connect(self.trigger_autoscale)
        self.ui.btn_run.toggled.connect(self.toggle_run_stop)
        
        # Kanalų rodymo mygtukų lambda funkcijos užtikrina tiek GUI, tiek aparatūros būsenos atnaujinimą
        self.ui.btn_osc_ch1.toggled.connect(lambda s: (self.set_display(s, 1), self.main.update_toggle_button_style(self.ui.btn_osc_ch1, s), self.main.curves[1].setVisible(s)))
        self.ui.btn_osc_ch2.toggled.connect(lambda s: (self.set_display(s, 2), self.main.update_toggle_button_style(self.ui.btn_osc_ch2, s), self.main.curves[2].setVisible(s)))
        self.ui.btn_osc_ch3.toggled.connect(lambda s: (self.set_display(s, 3), self.main.update_toggle_button_style(self.ui.btn_osc_ch3, s), self.main.curves[3].setVisible(s)))
        self.ui.btn_osc_ch4.toggled.connect(lambda s: (self.set_display(s, 4), self.main.update_toggle_button_style(self.ui.btn_osc_ch4, s), self.main.curves[4].setVisible(s)))
        
        # Susiejamas lentelės kanalo pasirinkimas (Combo box) su vizualiniu atnaujinimu
        self.ui.combo_meas_ch.currentIndexChanged.connect(self.display_channel_data)
        
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
        """Inicijuoja visų parametrų matavimą pasirinktam kanalui paleidžiant foninę giją."""
        if not self.mgr.osc: 
            self.main.log_msg("Klaida: Rigol neprijungtas!")
            return
            
        ch = self.ui.combo_meas_ch.currentIndex() + 1
        self.main.show_loading(f"Nuskaitomi Rigol CH{ch} parametrai...")
        
        # PALEIDŽIAMA NEBLOKUOJANTI GIJA
        threading.Thread(target=self._thread_read_all, args=(ch,), daemon=True).start()

    def _thread_read_all(self, ch):
        """
        Foninė funkcija: nuskaito 18 skirtingų parametrų per SCPI komandas.
        Apsaugota try...finally bloku, kad GUI nesustingtų net dingus ryšiui.
        """
        data = {}
        # Laikinai sustabdome stream, kad greičiau įvykdytume komandas
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.stream_timer.stop()
        
        try:
            # SCPI komandų ir matavimo vienetų žemėlapis
            params = [("VPP", "Vpp", "V"), ("VMAX", "Vmax", "V"), ("VMIN", "Vmin", "V"), ("VAMP", "Vamp", "V"),
                      ("VTOP", "Vtop", "V"), ("VBAS", "Vbase", "V"), ("VAVG", "Vavg", "V"), ("VRMS", "Vrms", "V"),
                      ("OVER", "Overshoot", "%"), ("PRE", "Preshoot", "%"), ("FREQ", "Freq", "Hz"), ("PER", "Period", "s"),
                      ("RTIM", "Rise Time", "s"), ("FTIM", "Fall Time", "s"), ("PWID", "Pulse (+)", "s"), ("NWID", "Pulse (-)", "s"),
                      ("PDUT", "Duty (+)", "%"), ("NDUT", "Duty (-)", "%")]
                      
            with self.mgr.lock:
                for cmd, name, unit in params:
                    try:
                        val = self.mgr.osc.get_measure(cmd, channel=ch)
                        # Jei ne klaida (ne > 1e15), formuojame gražų tekstą
                        if val is not None and val < 1e15:
                            data[name] = f"{val:.4e} {unit}"
                        else:
                            data[name] = "-"
                    except:
                        data[name] = "-"
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            # Visada išsiunčiamas signalas baigus skaitymą, kad uždarytų lentelę
            self.signals.meas_ready.emit(ch, data)
            if was_streaming: self.stream_timer.start(2000)
            
    def update_table(self, ch, data):
        """Signalo priėmėjas (GUI gijoje), išsaugantis duomenis atmintyje."""
        self.channel_data[ch] = data
        
        # Jei šiuo metu pasirinktas kanalas sutampa su nuskaitytu, iškart atvaizduojam
        if self.ui.combo_meas_ch.currentIndex() + 1 == ch:
            self.display_channel_data()
            
        self.main.hide_loading()
        self.main.log_msg(f"Rigol CH{ch} matavimai sėkmingai atnaujinti.")

    def display_channel_data(self):
        """Atvaizduoja iš atminties pasirinkto kanalo matavimus į UI lentelę."""
        ch = self.ui.combo_meas_ch.currentIndex() + 1
        data = self.channel_data[ch]
        
        self.ui.table_meas.setRowCount(len(data))
        for i, (k, v) in enumerate(data.items()):
            self.ui.table_meas.setItem(i, 0, QTableWidgetItem(k))
            self.ui.table_meas.setItem(i, 1, QTableWidgetItem(v))

    def on_error(self, msg):
        """Jei įvyksta kritinė ryšio klaida, krovimo lentelė vistiek paslepiama."""
        self.main.hide_loading()
        self.main.log_msg(f"Rigol Klaida: {msg}")

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
            
        if t is not None and len(t) > 1:
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
        Apsaugo nuo "trumpų" kreivių išzoominimo metu dinamiškai pririšdama ribas.
        """
        if not self.mgr.osc: return
        
        # Tikrinama, ar resursas neužrakintas kitų fono gijų (Bode, Logger)
        if not self.mgr.lock.locked():
            with self.mgr.lock:
                # Laikinas logavimo išjungimas, siekiant neapkrauti terminalo greito ciklo metu
                old_logger = self.mgr.osc.logger
                self.mgr.osc.logger = None  
                
                # Saugome mažiausią ir didžiausią laiko (X ašies) vertes kadro fiksavimui
                x_min, x_max = float('inf'), float('-inf')
                
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
                                
                                # Randame šio kadro kraštines vertes
                                if t[0] < x_min: x_min = t[0]
                                if t[-1] > x_max: x_max = t[-1]
                        else:
                            self.main.curves[ch].setData([], [])
                            self.main.curves[ch].setVisible(False)
                            
                    # Dinaminis mastelio koregavimas:
                    # Jei vartotojas nėra "įlindęs" į kreivę (t.y., atitolino pernelyg daug),
                    # pritraukiame ribas prie fizinių duomenų kraštų.
                    if x_min != float('inf') and x_max != float('-inf'):
                        view_box = self.ui.graph_widget.getViewBox()
                        current_x_range = view_box.viewRange()[0]
                        
                        # Jei esamas vaizdo plotas yra didesnis nei atsiunčiamų duomenų plotas (vartotojas išzoomino),
                        # užrakiname X ašį prie signalo rėmų
                        if current_x_range[0] < x_min or current_x_range[1] > x_max:
                            view_box.setXRange(x_min, x_max, padding=0)
                            
                finally: 
                    self.mgr.osc.logger = old_logger
                    
    def sync_ui(self):
        """Atgalinė sinchronizacija išjungta, siekiant išvengti UI konfliktų."""
        pass