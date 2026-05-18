from PyQt6.QtWidgets import QFileDialog, QMessageBox
from core.workers import DataLoggerWorker
import time

class LogController:
    """
    Ilgalaikio duomenų registravimo (Logger) valdiklis.
    Atsakingas už matuoklių (TTi 1604 arba Escort 3136A) paruošimą registravimui,
    failo išsaugojimo logiką ir foninės registravimo gijos (DataLoggerWorker) valdymą.
    """
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        
        self.worker = None
        
        # UI mygtukų signalų susiejimas su funkcijomis
        self.ui.btn_start_log.clicked.connect(self.start_logging)
        self.ui.btn_stop_log.clicked.connect(self.stop_logging)

    def start_logging(self):
        """
        Inicijuoja ilgalaikio matavimo procesą.
        Pirmiausia prašo vartotojo nurodyti failo išsaugojimo vietą,
        tuomet aparatūriškai sukonfigūruoja pasirinktą prietaisą ir paleidžia foninę giją.
        """
        # Atidaromas langas CSV failo lokacijai nurodyti
        fn, _ = QFileDialog.getSaveFileName(self.main, "Išsaugoti", "log.csv", "CSV (*.csv)")
        if not fn: return

        device_idx = self.ui.log_device.currentIndex()
        mode_txt = self.ui.log_mode.currentText()

        # Parodomas krovimo langas, nes prietaiso relių perjungimas užtrunka
        self.main.show_loading(f"Konfigūruojamas {self.ui.log_device.currentText()} ({mode_txt}). Laukite stabilizacijos...")
        self.main.repaint()

        with self.mgr.lock:
            if device_idx == 0 and self.mgr.tti:
                # TTi 1604 komandų formavimas pagal pasirinktą režimą
                cmds = []
                if "V" in mode_txt: cmds.append("V")
                if "A" in mode_txt and "mA" not in mode_txt: cmds.append("A")
                if "mA" in mode_txt: cmds.append("mA")
                if "OHM" in mode_txt: cmds.append("OHM")
                if "Hz" in mode_txt: cmds.append("FREQ")
                if "DC" in mode_txt: cmds.append("DC")
                if "AC" in mode_txt: cmds.append("AC")
                
                for c in cmds: 
                    self.mgr.tti.send_command(c)
                    
                # Laukiamas 1.5 s, kol TTi vidinės fizinės relės (Relays) persijungs ir stabilizuosis
                time.sleep(1.5) 
                
                # Nuskaitomas ir atmetamas pirmas rezultatas (šlamšto / pereinamųjų procesų išvalymui iš buferio)
                self.mgr.tti.get_reading() 
                    
            elif device_idx == 1 and self.mgr.esc:
                # Escort 3136A režimų kodų žemėlapis
                esc_cmds = {"V DC": "F0", "V AC": "F1", "OHM": "F2", "A DC": "F4", "A AC": "F5", "Hz": "F7"}
                if mode_txt in esc_cmds:
                    self.mgr.esc.send_command(esc_cmds[mode_txt])
                    
                    # Laukiamas 1 s, kol Escort stabilizuosis naujame režime
                    time.sleep(1.0)
                    self.mgr.esc.read_measurement()

        self.main.hide_loading()

        # Perjungiama į Logger grafiko skirtuką ir išvalomi seni duomenys
        self.ui.graph_tabs.setCurrentIndex(2)
        self.main.log_x.clear()
        self.main.log_y.clear()
        self.main.log_line.setData([], [])
        
        self.ui.btn_start_log.setEnabled(False)
        
        # Sukuriama ir paleidžiama foninė duomenų registravimo gija
        self.worker = DataLoggerWorker(
            self.mgr, 
            device_idx, 
            self.ui.log_mode.currentIndex(), 
            self.ui.log_interval.value(), 
            self.ui.log_duration.value(), 
            fn
        )
        self.worker.data_point.connect(self.on_log_data)
        self.worker.finished.connect(self.on_log_finished)
        self.worker.start()

    def on_log_data(self, t, val):
        """Priima naują matavimo tašką iš foninės gijos ir atnaujina grafiką."""
        self.main.log_x.append(t)
        self.main.log_y.append(val)
        self.main.log_line.setData(self.main.log_x, self.main.log_y)

    def stop_logging(self):
        """Nutraukia aktyvų duomenų registravimo procesą."""
        if self.worker: 
            self.worker.is_running = False

    def on_log_finished(self):
        """Atstato UI elementus į pradinę būseną po sėkmingo registravimo pabaigos."""
        self.ui.btn_start_log.setEnabled(True)
        self.main.log_msg("Ilgalaikis duomenų registravimas baigtas.")
        QMessageBox.information(self.main, "Registravimas Baigtas", "Duomenų sekimas baigtas ir išsaugotas CSV faile.")