from PyQt6.QtCore import QTimer
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class EscortController:
    def __init__(self, main, ui, mgr):
        self.main = main; self.ui = ui; self.mgr = mgr
        self.escort_unit = ""
        
        self.ui.combo_escort.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_esc_vdc.clicked.connect(lambda: self.set_func("F0", "V DC"))
        self.ui.btn_esc_vac.clicked.connect(lambda: self.set_func("F1", "V AC"))
        self.ui.btn_esc_ohm.clicked.connect(lambda: self.set_func("F2", "Ω"))
        self.ui.btn_esc_adc.clicked.connect(lambda: self.set_func("F4", "A DC"))
        self.ui.btn_esc_aac.clicked.connect(lambda: self.set_func("F5", "A AC"))
        self.ui.btn_esc_diode.clicked.connect(lambda: self.set_func("F6", "V"))
        self.ui.btn_esc_hz.clicked.connect(lambda: self.set_func("F7", "Hz"))
        self.ui.btn_esc_read_all.clicked.connect(self.refresh)

    def _on_changed(self):
        port = self.ui.combo_escort.currentData()
        if port and port == self.ui.combo_tti.currentData():
            self.ui.combo_tti.blockSignals(True); self.ui.combo_tti.setCurrentIndex(0); self.ui.combo_tti.blockSignals(False)
            with self.mgr.lock:
                if self.mgr.tti: self.mgr.tti.close(); self.mgr.tti = None
        if port: self.mgr.connect_esc(port)
        else:
            with self.mgr.lock:
                if self.mgr.esc: self.mgr.esc.close(); self.mgr.esc = None

    def set_func(self, cmd, default_unit):
        if not self.mgr.esc: return self.main.log_msg("Klaida: Escort neprijungtas.")
        self.escort_unit = default_unit
        self.main.show_loading(f"Konfigūruojamas Escort ({default_unit})...")
        QTimer.singleShot(100, lambda: (self.mgr.lock.acquire(), self.mgr.esc.send_command(cmd), self.mgr.lock.release(), self.main.hide_loading(), QTimer.singleShot(500, self.refresh)))

    def refresh(self):
        if not self.mgr.esc: return
        self.main.show_loading("Nuskaitomi duomenys iš Escort...")
        QTimer.singleShot(100, self._perform_refresh)

    def _perform_refresh(self):
        with self.mgr.lock:
            val, unit = self.mgr.esc.read_measurement()
            if val is not None: 
                disp_u = unit if unit else self.escort_unit
                self.ui.lbl_esc_val.setText(f"{val} {disp_u}".strip())
                self.ui.lbl_esc_val.setStyleSheet(STYLE_LCD_AC if "AC" in disp_u or "Hz" in disp_u else STYLE_LCD_DC)
            else: self.ui.lbl_esc_val.setText("KLAIDA")
        self.main.hide_loading()