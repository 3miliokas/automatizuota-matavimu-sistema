from PyQt6.QtWidgets import QFileDialog, QMessageBox
from core.workers import DataLoggerWorker
import time

class LogController:
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        
        self.worker = None
        self.ui.btn_start_log.clicked.connect(self.start_logging)
        self.ui.btn_stop_log.clicked.connect(self.stop_logging)

    def start_logging(self):
        fn, _ = QFileDialog.getSaveFileName(self.main, "Išsaugoti", "log.csv", "CSV (*.csv)")
        if not fn: return

        device_idx = self.ui.log_device.currentIndex()
        mode_txt = self.ui.log_mode.currentText()

        self.main.show_loading(f"Konfigūruojamas {self.ui.log_device.currentText()} ({mode_txt}). Laukite stabilizacijos...")
        self.main.repaint()

        with self.mgr.lock:
            if device_idx == 0 and self.mgr.tti:
                cmds = []
                if "V" in mode_txt: cmds.append("V")
                if "A" in mode_txt and "mA" not in mode_txt: cmds.append("A")
                if "mA" in mode_txt: cmds.append("mA")
                if "OHM" in mode_txt: cmds.append("OHM")
                if "Hz" in mode_txt: cmds.append("FREQ")
                if "DC" in mode_txt: cmds.append("DC")
                if "AC" in mode_txt: cmds.append("AC")
                
                for c in cmds: self.mgr.tti.send_command(c)
                time.sleep(1.5) # Relays
                self.mgr.tti.get_reading() # Skaitymas atmetamas (šlamštui išvalyti po relay jungimo)
                    
            elif device_idx == 1 and self.mgr.esc:
                esc_cmds = {"V DC": "F0", "V AC": "F1", "OHM": "F2", "A DC": "F4", "A AC": "F5", "Hz": "F7"}
                if mode_txt in esc_cmds:
                    self.mgr.esc.send_command(esc_cmds[mode_txt])
                    time.sleep(1.0)
                    self.mgr.esc.read_measurement()

        self.main.hide_loading()

        self.ui.graph_tabs.setCurrentIndex(2)
        self.main.log_x.clear(); self.main.log_y.clear(); self.main.log_line.setData([], [])
        self.ui.btn_start_log.setEnabled(False)
        
        self.worker = DataLoggerWorker(self.mgr, device_idx, self.ui.log_mode.currentIndex(), self.ui.log_interval.value(), self.ui.log_duration.value(), fn)
        self.worker.data_point.connect(self.on_log_data)
        self.worker.finished.connect(self.on_log_finished)
        self.worker.start()

    def on_log_data(self, t, val):
        self.main.log_x.append(t)
        self.main.log_y.append(val)
        self.main.log_line.setData(self.main.log_x, self.main.log_y)

    def stop_logging(self):
        if self.worker: self.worker.is_running = False

    def on_log_finished(self):
        self.ui.btn_start_log.setEnabled(True)
        self.main.log_msg("Ilgalaikis duomenų registravimas baigtas.")
        QMessageBox.information(self.main, "Registravimas Baigtas", "Duomenų sekimas baigtas ir išsaugotas CSV faile.")