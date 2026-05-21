import threading
from PyQt6.QtCore import pyqtSignal, QObject
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class EscSignals(QObject):
    data_ready = pyqtSignal(object, str)

class EscortController:
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        self.escort_unit = ""
        self.signals = EscSignals()
        self.signals.data_ready.connect(self._update_display)
        
        self.ui.combo_escort.currentIndexChanged.connect(self._on_changed)
        
        self.ui.btn_esc_vdc.clicked.connect(lambda: self.set_func("S100", "V DC"))
        self.ui.btn_esc_vac.clicked.connect(lambda: self.set_func("S110", "V AC"))
        self.ui.btn_esc_ohm.clicked.connect(lambda: self.set_func("S120", "Ω"))
        self.ui.btn_esc_adc.clicked.connect(lambda: self.set_func("S140", "A DC"))
        self.ui.btn_esc_aac.clicked.connect(lambda: self.set_func("S150", "A AC"))
        self.ui.btn_esc_diode.clicked.connect(lambda: self.set_func("S160", "V"))
        self.ui.btn_esc_hz.clicked.connect(lambda: self.set_func("S170", "Hz"))
        self.ui.btn_esc_dbm.clicked.connect(lambda: self.set_func("S1B0", "dBm"))
        self.ui.btn_esc_cont.clicked.connect(lambda: self.set_func("S1A0", "Continuity"))

        self.ui.btn_esc_read_all.clicked.connect(self.refresh)

    def _on_changed(self):
        port = self.ui.combo_escort.currentData()
        if port and port == self.ui.combo_tti.currentData():
            self.ui.combo_tti.blockSignals(True)
            self.ui.combo_tti.setCurrentIndex(0)
            self.ui.combo_tti.blockSignals(False)
            with self.mgr.lock:
                if self.mgr.tti: 
                    self.mgr.tti.close()
                    self.mgr.tti = None
                    
        if port: self.mgr.connect_esc(port)
        else:
            with self.mgr.lock:
                if self.mgr.esc: 
                    self.mgr.esc.close()
                    self.mgr.esc = None

    def set_buttons_state(self, state):
        for btn in [self.ui.btn_esc_vdc, self.ui.btn_esc_vac, self.ui.btn_esc_ohm, 
                    self.ui.btn_esc_adc, self.ui.btn_esc_aac, self.ui.btn_esc_diode, 
                    self.ui.btn_esc_hz, self.ui.btn_esc_dbm, self.ui.btn_esc_cont, 
                    self.ui.btn_esc_read_all]:
            btn.setEnabled(state)

    def set_func(self, cmd, default_unit):
        if not self.mgr.esc: return
        self.escort_unit = default_unit
        self.set_buttons_state(False)
        self.main.show_loading(f"Konfigūruojamas Escort ({default_unit})...")
        threading.Thread(target=self._thread_cmd, args=(cmd,), daemon=True).start()

    def _thread_cmd(self, cmd):
        import time
        val, unit = None, ""
        try:
            with self.mgr.lock:
                self.mgr.esc.send_command(cmd)
                time.sleep(0.5)
                val, unit = self.mgr.esc.read_measurement()
        finally:
            self.signals.data_ready.emit(val, unit)

    def refresh(self):
        if not self.mgr.esc: return
        self.set_buttons_state(False)
        self.main.show_loading("Nuskaitomi duomenys iš Escort...")
        threading.Thread(target=self._thread_refresh, daemon=True).start()

    def _thread_refresh(self):
        val, unit = None, ""
        try:
            with self.mgr.lock:
                val, unit = self.mgr.esc.read_measurement()
        finally:
            self.signals.data_ready.emit(val, unit)

    def _update_display(self, val, unit):
        if val is not None: 
            disp_u = unit if unit else self.escort_unit
            self.ui.lbl_esc_val.setText(f"{val} {disp_u}".strip())
            self.ui.lbl_esc_val.setStyleSheet(STYLE_LCD_AC if "AC" in disp_u or "Hz" in disp_u else STYLE_LCD_DC)
        else: 
            self.ui.lbl_esc_val.setText("KLAIDA")
            
        self.main.hide_loading()
        self.set_buttons_state(True)