import threading
from PyQt6.QtCore import pyqtSignal, QObject
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class TtiSignals(QObject):
    # Signalas, skirtas saugiai perduoti duomenis iš fono gijos į GUI.
    data_ready = pyqtSignal(object, str, str)

class TtiController:
    """
    TTi 1604 stalinio multimetro valdymo valdiklis.
    Apdoroja mygtukų paspaudimus, siunčia RS-232 komandas fone,
    atnaujina ekranėlį (Label) bei realizuoja programinę "NULL" (poslinkio) funkciją.
    """
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        
        # Programinis nulio nustatymas (offset). 
        # Kadangi prietaisas per RS-232 to natūraliai nepalaiko, tai atliekama programiškai.
        self.software_offset = 0.0
        self.last_val = None
        
        self.signals = TtiSignals()
        self.signals.data_ready.connect(self._update_display)
        
        self.ui.combo_tti.currentIndexChanged.connect(self._on_changed)

        # Standartinių komandų susiejimas
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
        
        # Specifinių mygtukų konfigūravimas pagal realų prietaiso atsaką
        # Pvz., Dažniui ir Grandinės vientisumui reikia spausti SHIFT + V arba SHIFT + OHM
        self.ui.btn_tti_diode.clicked.connect(lambda: self.send_shift_macro("V", "Frequency (Hz)"))
        self.ui.btn_tti_hz.clicked.connect(lambda: self.send_cmd("FREQ")) # Remiantis originaliu TTi kodu (kartais DIODE žymimas kaip FREQ)
        self.ui.btn_tti_cont.clicked.connect(lambda: self.send_shift_macro("OHM", "Continuity"))

        self.ui.btn_tti_reset.clicked.connect(lambda: self.send_cmd("RESET"))
        self.ui.btn_tti_refresh.clicked.connect(self.refresh)
        self.ui.btn_tti_null.toggled.connect(self.toggle_null)

    def _on_changed(self):
        """Užkerta kelią prievado dubliavimuisi tarp Escort ir TTi įrenginių."""
        port = self.ui.combo_tti.currentData()
        if port and port == self.ui.combo_escort.currentData():
            self.ui.combo_escort.blockSignals(True)
            self.ui.combo_escort.setCurrentIndex(0)
            self.ui.combo_escort.blockSignals(False)
            with self.mgr.lock:
                if self.mgr.esc: 
                    self.mgr.esc.close()
                    self.mgr.esc = None
        if port: 
            self.mgr.connect_tti(port)
        else:
            with self.mgr.lock:
                if self.mgr.tti: 
                    self.mgr.tti.close()
                    self.mgr.tti = None

    def set_buttons_state(self, state):
        """Blokuoja mygtukus komandos vykdymo metu, kad nebūtų persidengimų."""
        for btn in [self.ui.btn_tti_operate, self.ui.btn_tti_up, self.ui.btn_tti_down, self.ui.btn_tti_auto,
                    self.ui.btn_tti_v, self.ui.btn_tti_a, self.ui.btn_tti_ma, self.ui.btn_tti_mv,
                    self.ui.btn_tti_dc, self.ui.btn_tti_ac, self.ui.btn_tti_ohm, self.ui.btn_tti_hz,
                    self.ui.btn_tti_diode, self.ui.btn_tti_cont, self.ui.btn_tti_reset, self.ui.btn_tti_refresh,
                    self.ui.btn_tti_null]:
            btn.setEnabled(state)

    def send_cmd(self, cmd):
        """Inicijuoja standartinės komandos siuntimą per foninę giją."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading(f"Siunčiama: '{cmd}'...")
        threading.Thread(target=self._thread_cmd, args=(cmd,), daemon=True).start()

    def _thread_cmd(self, cmd):
        """Siunčia komandą fone su apsauga nuo UI pakibimo."""
        val, unit, mode = None, "", ""
        try:
            with self.mgr.lock:
                self.mgr.tti.send_command(cmd)
                val, unit, mode = self.mgr.tti.get_reading()
        finally:
            self.signals.data_ready.emit(val, unit, mode)

    def send_shift_macro(self, cmd, desc):
        """Inicijuoja dviejų mygtukų kombinacijos (pvz., SHIFT + V) siuntimą."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading(f"Siunčiama: SHIFT + {cmd}...")
        threading.Thread(target=self._thread_shift, args=(cmd,), daemon=True).start()

    def _thread_shift(self, cmd):
        """Siunčia komandų kombinaciją fone su apsauga."""
        val, unit, mode = None, "", ""
        try:
            with self.mgr.lock:
                self.mgr.tti.send_command("SHIFT")
                self.mgr.tti.send_command(cmd)
                val, unit, mode = self.mgr.tti.get_reading()
        finally:
            self.signals.data_ready.emit(val, unit, mode)

    def refresh(self):
        """Momentinis reikšmės nuskaitymas (Refresh)."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Nuskaitoma iš TTi 1604...")
        threading.Thread(target=self._thread_refresh, daemon=True).start()

    def _thread_refresh(self):
        """Nuskaito duomenis fone be komandos keitimo."""
        val, unit, mode = None, "", ""
        try:
            with self.mgr.lock:
                val, unit, mode = self.mgr.tti.get_reading()
        finally:
            self.signals.data_ready.emit(val, unit, mode)

    def _update_display(self, val, unit, mode):
        """
        Gautos reikšmės apdorojimas (GUI gijoje). 
        Čia pritaikomas ir programinis Null poslinkis (Offset).
        """
        self.last_val = val
        if val is not None:
            if val == float('inf'): 
                txt = "OFL" # Overload (viršytas limitas)
            else:
                # Pritaikome apskaičiuotą poslinkį
                adj_val = val - self.software_offset
                txt = f"{adj_val:.4f}"
                
            self.ui.lbl_tti_val.setText(f"{txt} {unit} {mode}".strip())
            # AC signalams pritaikomas kitoks vizualinis LED fono stilius
            self.ui.lbl_tti_val.setStyleSheet(STYLE_LCD_AC if "AC" in mode else STYLE_LCD_DC)
        else:
            self.ui.lbl_tti_val.setText("KLAIDA")
            
        # Privalomai išjungiama krovimo lentelė ir aktyvuojami mygtukai
        self.main.hide_loading()
        self.set_buttons_state(True)

    def toggle_null(self, state):
        """
        Įjungia/Išjungia programinį matavimo nulio nustatymą.
        Kitas matavimas bus skaičiuojamas nuo šios reikšmės.
        """
        if state:
            if self.last_val is not None and self.last_val != float('inf'):
                # Fiksuojame momentinę reikšmę kaip naują atskaitos tašką
                self.software_offset = self.last_val
                self.main.update_toggle_button_style(self.ui.btn_tti_null, True)
            else:
                # Jei reikšmė nevalidi, atšaukiame paspaudimą
                self.ui.btn_tti_null.blockSignals(True)
                self.ui.btn_tti_null.setChecked(False)
                self.ui.btn_tti_null.blockSignals(False)
        else:
            # Išjungiame poslinkį
            self.software_offset = 0.0
            self.main.update_toggle_button_style(self.ui.btn_tti_null, False)
            
        # Iškart perskaičiuojame atvaizduojamą tekstą su nauju poslinkiu
        if self.last_val is not None and self.last_val != float('inf'):
            adj_val = self.last_val - self.software_offset
            parts = self.ui.lbl_tti_val.text().split(" ", 1)
            if len(parts) > 1: 
                self.ui.lbl_tti_val.setText(f"{adj_val:.4f} {parts[1]}")