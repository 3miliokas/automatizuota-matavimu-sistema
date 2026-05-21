from PyQt6.QtWidgets import QFileDialog, QMessageBox
from core.workers import DataLoggerWorker

class LogController:
    """
    Ilgalaikio duomenų registravimo (Logger) valdiklis.
    Ši klasė valdo GUI elementus "Logger" skirtuke, dinamiškai pritaiko matavimo
    parametrus priklausomai nuo pasirinkto prietaiso ir sukuria foninę giją
    nenutrūkstamam duomenų rašymui į CSV failą bei atvaizdavimui realiu laiku.
    """
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        self.worker = None
        
        # Dinaminis matavimo režimų atnaujinimas, kai vartotojas pakeičia prietaisą
        self.ui.log_device.currentIndexChanged.connect(self.update_log_modes)
        self.update_log_modes() # Sukuriame pradinį sąrašą užkraunant programą
        
        # Mygtukų susiejimas su funkcijomis
        self.ui.btn_start_log.clicked.connect(self.start_logging)
        self.ui.btn_stop_log.clicked.connect(self.stop_logging)

    def update_log_modes(self):
        """
        Dinamiškai atnaujina galimų matavimo parametrų sąrašą išskleidžiamajame meniu (ComboBox)
        priklausomai nuo to, kurį prietaisą (Rigol, TTi, Escort) pasirinko vartotojas.
        """
        self.ui.log_mode.clear()
        idx = self.ui.log_device.currentIndex()
        
        if idx == 0:
            # Rigol MSO oscilografas palaiko tiesioginį SCPI komandų parametrų matavimą
            self.ui.log_mode.addItems([
                "VPP", "VMAX", "VMIN", "VAMP", "VTOP", "VBAS", "VAVG", "VRMS", 
                "OVER", "PRE", "FREQ", "PER", "PWID", "NWID", "PDUT", "NDUT", "RTIM", "FTIM"
            ])
        elif idx == 1:
            # TTi 1604 multimetras
            self.ui.log_mode.addItems(["V DC", "V AC", "A DC", "A AC", "mA DC", "mA AC", "OHM", "Hz"])
        elif idx == 2:
            # Escort 3136A multimetras
            self.ui.log_mode.addItems(["V DC", "V AC", "A DC", "A AC", "Ω", "Continuity", "Hz", "dBm", "Diode"])

    def start_logging(self):
        """
        Validuoja vartotojo įvestį, surenka nustatymus ir inicijuoja fono giją
        (DataLoggerWorker) duomenų registravimui.
        """
        device_idx = self.ui.log_device.currentIndex()
        osc_channel = self.ui.log_osc_ch.currentIndex() + 1 
        
        # 1. Aparatūros prieinamumo patikra
        if device_idx == 0 and not self.mgr.osc:
            QMessageBox.critical(self.main, "Klaida", "Neprijungtas Rigol MSO oscilografas!")
            return
        if device_idx == 1 and not self.mgr.tti:
            QMessageBox.critical(self.main, "Klaida", "Neprijungtas TTi 1604 multimetras!")
            return
        if device_idx == 2 and not self.mgr.esc:
            QMessageBox.critical(self.main, "Klaida", "Neprijungtas Escort 3136A multimetras!")
            return

        # 2. Laiko parametrų konversija į bazinius vienetus (ms ir s)
        int_units = {"ms": 1, "s": 1000, "min": 60000}
        dur_units = {"s": 1, "min": 60, "h": 3600}
        
        interval_ms = int(self.ui.log_interval.value() * int_units[self.ui.log_interval_unit.currentText()])
        duration_s = int(self.ui.log_duration.value() * dur_units[self.ui.log_duration_unit.currentText()])
        
        # Validacija: matavimo intervalas negali būti ilgesnis už bendrą matavimo trukmę
        if duration_s > 0 and (interval_ms / 1000) > duration_s:
            QMessageBox.warning(self.main, "Klaida", "Intervalas negali būti ilgesnis už bendrą trukmę!")
            return

        # 3. Failo pasirinkimo dialogas
        fn, _ = QFileDialog.getSaveFileName(self.main, "Išsaugoti", "log.csv", "CSV (*.csv)")
        if not fn: return

        # 4. GUI grafiko paruošimas
        self.ui.graph_tabs.setCurrentIndex(2)
        self.main.log_x.clear()
        self.main.log_y.clear()
        self.main.log_line.setData([], [])
        
        self.ui.btn_start_log.setEnabled(False)
        self.ui.log_progress.setValue(0)
        
        # 5. Fono gijos kūrimas ir paleidimas
        self.worker = DataLoggerWorker(
            self.mgr, 
            device_idx, 
            self.ui.log_mode.currentText(), 
            interval_ms, 
            duration_s, 
            fn,
            osc_channel  
        )
        
        # Susiejame fono gijos signalus su GUI atnaujinimo funkcijomis
        self.worker.data_point.connect(self.on_log_data)
        self.worker.progress.connect(self.ui.log_progress.setValue)
        self.worker.finished.connect(self.on_log_finished)
        
        # KLAIDOS SIGNALO SUJUNGIMAS (Trūkstama dalis, dėl kurios nesimatė lūžimo)
        self.worker.error.connect(self.on_log_error)
        
        self.worker.start()

    def on_log_data(self, t, val):
        """
        Grįžtamojo ryšio signalo (Callback) funkcija, atnaujinanti grafiką po kiekvieno taško.
        """
        MAX_POINTS = 2000
        
        self.main.log_x.append(t)
        self.main.log_y.append(val)
        
        if len(self.main.log_x) > MAX_POINTS:
            self.main.log_x.pop(0)
            self.main.log_y.pop(0)
            
        self.main.log_line.setData(self.main.log_x, self.main.log_y)
        self.ui.lbl_log_current.setText(f"Dabartinė: {val:.4e}")

    def stop_logging(self):
        """Saugiai sustabdo fono giją."""
        if self.worker: 
            self.worker.is_running = False

    def on_log_finished(self):
        """Atblokuoja UI elementus, kai matavimo gija sėkmingai baigia darbą."""
        self.ui.btn_start_log.setEnabled(True)
        self.main.log_msg("Ilgalaikis duomenų registravimas baigtas.")
        QMessageBox.information(self.main, "Baigta", "Duomenys išsaugoti CSV faile.")
        
    def on_log_error(self, err_msg):
        """Iškviečiama, jei DataLoggerWorker patiria kritinę klaidą fone."""
        self.ui.btn_start_log.setEnabled(True)
        self.ui.log_progress.setValue(0)
        self.main.log_msg(f"Logger klaida: {err_msg}")
        QMessageBox.critical(self.main, "Gijos Klaida", f"Duomenų registravimas nutrūko:\n{err_msg}")