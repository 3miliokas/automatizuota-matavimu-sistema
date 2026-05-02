from PyQt6.QtCore import QTimer
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class TtiController:
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        
        self.software_offset = 0.0
        self.last_val = None

        # Trūko šio susiejimo:
        self.ui.combo_tti.currentIndexChanged.connect(self._on_changed)

        self.ui.btn_tti_operate.clicked.connect(lambda: self.send_cmd("OPERATE"))
        self.ui.btn_tti_up.clicked.connect(lambda: self.send_cmd("UP"))
        self.ui.btn_tti_down.clicked.connect(lambda: self.send_cmd("DOWN"))
        self.ui.btn_tti_auto.clicked.connect(lambda: self.send_cmd("AUTO"))
        self.ui.btn_tti_v.clicked.connect(lambda: self.send_cmd("V"))
        self.ui.btn_tti_a.clicked.connect(lambda: self.send_cmd("A"))
        self.ui.btn_tti_ma.clicked.connect(lambda: self.send_cmd("mA"))
        self.ui.btn_tti_mv.clicked.connect(lambda: self.send_cmd("mV"))
        self.ui.btn_tti_dc.clicked.connect(lambda: self.send_cmd("DC"))
        self.ui.btn_tti_ac.clicked.connect(lambda: self.send_cmd("AC"))
        self.ui.btn_tti_ohm.clicked.connect(lambda: self.send_cmd("OHM"))
        self.ui.btn_tti_hz.clicked.connect(lambda: self.send_cmd("FREQ"))
        
        self.ui.btn_tti_diode.clicked.connect(self.send_diode)
        self.ui.btn_tti_cont.clicked.connect(self.send_cont)
        self.ui.btn_tti_reset.clicked.connect(self.send_reset)
        self.ui.btn_tti_refresh.clicked.connect(self.refresh)
        self.ui.btn_tti_null.toggled.connect(self.toggle_null)

    def _on_changed(self):
        port = self.ui.combo_tti.currentData()
        if port and port == self.ui.combo_escort.currentData():
            self.ui.combo_escort.blockSignals(True)
            self.ui.combo_escort.setCurrentIndex(0)
            self.ui.combo_escort.blockSignals(False)
            with self.mgr.lock:
                if self.mgr.esc: self.mgr.esc.close(); self.mgr.esc = None
                
        if port: self.mgr.connect_tti(port)
        else:
            with self.mgr.lock:
                if self.mgr.tti: self.mgr.tti.close(); self.mgr.tti = None

    def set_buttons_state(self, state):
        for btn in [self.ui.btn_tti_operate, self.ui.btn_tti_up, self.ui.btn_tti_down, self.ui.btn_tti_auto,
                    self.ui.btn_tti_v, self.ui.btn_tti_a, self.ui.btn_tti_ma, self.ui.btn_tti_mv,
                    self.ui.btn_tti_dc, self.ui.btn_tti_ac, self.ui.btn_tti_ohm, self.ui.btn_tti_hz,
                    self.ui.btn_tti_diode, self.ui.btn_tti_cont, self.ui.btn_tti_reset, self.ui.btn_tti_refresh,
                    self.ui.btn_tti_null]:
            btn.setEnabled(state)

    def send_cmd(self, cmd):
        if not self.mgr.tti: return self.main.log_msg("Klaida: TTi 1604 neprijungtas.")
        self.set_buttons_state(False)
        self.main.show_loading(f"Siunčiama komanda '{cmd}'...")
        QTimer.singleShot(100, lambda: self._perform_cmd(cmd))

    def _perform_cmd(self, cmd):
        with self.mgr.lock: self.mgr.tti.send_command(cmd)
        self.main.hide_loading()
        QTimer.singleShot(100, self.refresh)

    def refresh(self):
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Nuskaitoma iš TTi 1604...")
        QTimer.singleShot(100, self._perform_refresh)

    def _perform_refresh(self):
        with self.mgr.lock:
            val, unit, mode = self.mgr.tti.get_reading()
            self.last_val = val
            if val is not None:
                if val == float('inf'):
                    txt = "OFL"
                else:
                    adj_val = val - self.software_offset
                    txt = f"{adj_val:.4f}"
                self.ui.lbl_tti_val.setText(f"{txt} {unit} {mode}".strip())
                self.ui.lbl_tti_val.setStyleSheet(STYLE_LCD_AC if "AC" in mode else STYLE_LCD_DC)
            else:
                self.ui.lbl_tti_val.setText("KLAIDA")
        self.main.hide_loading()
        self.set_buttons_state(True)

    def toggle_null(self, state):
        if state:
            if self.last_val is not None and self.last_val != float('inf'):
                self.software_offset = self.last_val
                self.main.update_toggle_button_style(self.ui.btn_tti_null, True)
            else:
                self.ui.btn_tti_null.blockSignals(True)
                self.ui.btn_tti_null.setChecked(False)
                self.ui.btn_tti_null.blockSignals(False)
        else:
            self.software_offset = 0.0
            self.main.update_toggle_button_style(self.ui.btn_tti_null, False)
        if self.last_val is not None and self.last_val != float('inf'):
            adj_val = self.last_val - self.software_offset
            parts = self.ui.lbl_tti_val.text().split(" ", 1)
            if len(parts) > 1:
                self.ui.lbl_tti_val.setText(f"{adj_val:.4f} {parts[1]}")

    def send_diode(self):
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Aktyvuojamas Diode Test...")
        QTimer.singleShot(100, lambda: (self.mgr.lock.acquire(), self.mgr.tti.send_command("SHIFT"), self.mgr.tti.send_command("V"), self.mgr.lock.release(), self.main.hide_loading(), QTimer.singleShot(100, self.refresh)))

    def send_cont(self):
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Aktyvuojamas Continuity Test...")
        QTimer.singleShot(100, lambda: (self.mgr.lock.acquire(), self.mgr.tti.send_command("SHIFT"), self.mgr.tti.send_command("OHM"), self.mgr.lock.release(), self.main.hide_loading(), QTimer.singleShot(100, self.refresh)))

    def send_reset(self):
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("RESET...")
        QTimer.singleShot(100, lambda: (self.mgr.lock.acquire(), self.mgr.tti.send_command("V"), self.mgr.tti.send_command("DC"), self.mgr.tti.send_command("AUTO"), self.mgr.lock.release(), self.ui.btn_tti_null.setChecked(False), self.main.hide_loading(), QTimer.singleShot(100, self.refresh)))