from PyQt6.QtCore import QTimer
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class TtiController:
    """
    TTi 1604 stalinio multimetro valdymo valdiklis.
    Apdoroja prietaiso mygtukų paspaudimus GUI sąsajoje, formatuoja išsiunčiamas
    komandas, realizuoja programinį duomenų kalibravimą (NULL/Zero funkciją) 
    bei atnaujina virtualų LCD ekraną.
    """
    def __init__(self, main_win, ui, mgr):
        self.main = main_win
        self.ui = ui
        self.mgr = mgr
        
        self.software_offset = 0.0
        self.last_val = None

        self.ui.combo_tti.currentIndexChanged.connect(self._on_changed)

        # Standartinių prietaiso skydelio mygtukų susiejimas per lambda funkcijas
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
        
        # Specifinių matavimų (kuriems reikia SHIFT komandos) ir pagalbiniai mygtukai
        self.ui.btn_tti_diode.clicked.connect(self.send_diode)
        self.ui.btn_tti_cont.clicked.connect(self.send_cont)
        self.ui.btn_tti_reset.clicked.connect(self.send_reset)
        self.ui.btn_tti_refresh.clicked.connect(self.refresh)
        self.ui.btn_tti_null.toggled.connect(self.toggle_null)

    def _on_changed(self):
        """
        Apdoroja COM prievado pasikeitimą išskleidžiamajame sąraše.
        Integruota apsauga nuo prievadų konfliktų: jei pasirenkamas prievadas,
        kurį jau naudoja Escort multimetras, Escort ryšys automatiškai nutraukiamas.
        """
        port = self.ui.combo_tti.currentData()
        
        # Patikrinama, ar prievadas jau nėra užimtas kito multimetro (Escort)
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
        """
        Blokuoja arba atblokuoja visus valdymo mygtukus.
        Naudojama komandų siuntimo metu (apsaugai nuo vartotojo įvesčių kolizijos).
        """
        for btn in [self.ui.btn_tti_operate, self.ui.btn_tti_up, self.ui.btn_tti_down, self.ui.btn_tti_auto,
                    self.ui.btn_tti_v, self.ui.btn_tti_a, self.ui.btn_tti_ma, self.ui.btn_tti_mv,
                    self.ui.btn_tti_dc, self.ui.btn_tti_ac, self.ui.btn_tti_ohm, self.ui.btn_tti_hz,
                    self.ui.btn_tti_diode, self.ui.btn_tti_cont, self.ui.btn_tti_reset, self.ui.btn_tti_refresh,
                    self.ui.btn_tti_null]:
            btn.setEnabled(state)

    def send_cmd(self, cmd):
        """Asinchroniškai išsiunčia standartinę vieno mygtuko paspaudimo komandą į TTi."""
        if not self.mgr.tti: return self.main.log_msg("Klaida: TTi 1604 neprijungtas.")
        self.set_buttons_state(False)
        self.main.show_loading(f"Siunčiama komanda '{cmd}'...")
        QTimer.singleShot(100, lambda: self._perform_cmd(cmd))

    def _perform_cmd(self, cmd):
        """Fiziškai išsiunčia komandą užrakintoje magistralėje ir inicijuoja ekrano atnaujinimą."""
        with self.mgr.lock: 
            self.mgr.tti.send_command(cmd)
        self.main.hide_loading()
        QTimer.singleShot(100, self.refresh)

    def refresh(self):
        """Inicijuoja momentinę duomenų akviziciją iš prietaiso."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Nuskaitoma iš TTi 1604...")
        QTimer.singleShot(100, self._perform_refresh)

    def _perform_refresh(self):
        """
        Nuskaito iškoduotus binarinius duomenis, pritaiko programinį
        matavimo poslinkį (jei aktyvus) ir atnaujina virtualų LCD ekraną.
        """
        with self.mgr.lock:
            val, unit, mode = self.mgr.tti.get_reading()
            self.last_val = val
            
            if val is not None:
                if val == float('inf'):
                    txt = "OFL" # Overload indikacija
                else:
                    # Programinis kalibravimas (NULL) - iš reikšmės atimamas užfiksuotas poslinkis
                    adj_val = val - self.software_offset
                    txt = f"{adj_val:.4f}"
                    
                self.ui.lbl_tti_val.setText(f"{txt} {unit} {mode}".strip())
                # Stilius: kintamoji srovė oranžine, nuolatinė žalia spalva
                self.ui.lbl_tti_val.setStyleSheet(STYLE_LCD_AC if "AC" in mode else STYLE_LCD_DC)
            else:
                self.ui.lbl_tti_val.setText("KLAIDA")
                
        self.main.hide_loading()
        self.set_buttons_state(True)

    def toggle_null(self, state):
        """
        Valdo programinio kalibravimo (NULL / Relative) funkciją.
        Kai aktyvuota, paskutinis matavimas išsaugomas kaip etaloninis nulis ir
        nuolat atimamas iš tolesnių gautų duomenų.
        """
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
            
        # Dinamiškai perskaičiuojamas jau ekrane rodomas rodmuo pritaikius arba nuėmus filtrą
        if self.last_val is not None and self.last_val != float('inf'):
            adj_val = self.last_val - self.software_offset
            parts = self.ui.lbl_tti_val.text().split(" ", 1)
            if len(parts) > 1:
                self.ui.lbl_tti_val.setText(f"{adj_val:.4f} {parts[1]}")

    def send_diode(self):
        """Aktyvuoja diodų testavimą (fiziniame prietaise reikalauja SHIFT + V komandų sekos)."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Aktyvuojamas Diode Test...")
        QTimer.singleShot(100, lambda: (
            self.mgr.lock.acquire(), 
            self.mgr.tti.send_command("SHIFT"), 
            self.mgr.tti.send_command("V"), 
            self.mgr.lock.release(), 
            self.main.hide_loading(), 
            QTimer.singleShot(100, self.refresh)
        ))

    def send_cont(self):
        """Aktyvuoja grandinės vientisumo testavimą (SHIFT + OHM)."""
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("Aktyvuojamas Continuity Test...")
        QTimer.singleShot(100, lambda: (
            self.mgr.lock.acquire(), 
            self.mgr.tti.send_command("SHIFT"), 
            self.mgr.tti.send_command("OHM"), 
            self.mgr.lock.release(), 
            self.main.hide_loading(), 
            QTimer.singleShot(100, self.refresh)
        ))

    def send_reset(self):
        """
        Išsiunčia komandų seką, grąžinančią prietaisą į pradinę, saugią būseną:
        Nuolatinės įtampos matavimas automatinio mastelio (Auto-range) režimu.
        Taip pat atšaukia programinį NULL kalibravimą.
        """
        if not self.mgr.tti: return
        self.set_buttons_state(False)
        self.main.show_loading("RESET...")
        QTimer.singleShot(100, lambda: (
            self.mgr.lock.acquire(), 
            self.mgr.tti.send_command("V"), 
            self.mgr.tti.send_command("DC"), 
            self.mgr.tti.send_command("AUTO"), 
            self.mgr.lock.release(), 
            self.ui.btn_tti_null.setChecked(False), 
            self.main.hide_loading(), 
            QTimer.singleShot(100, self.refresh)
        ))