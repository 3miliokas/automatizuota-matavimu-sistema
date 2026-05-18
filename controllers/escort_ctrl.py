from PyQt6.QtCore import QTimer
from gui.theme import STYLE_LCD_AC, STYLE_LCD_DC

class EscortController:
    """
    Escort 3136A multimetro valdymo valdiklis.
    Atsakingas už grafinės vartotojo sąsajos mygtukų paspaudimų apdorojimą,
    komandų siuntimą į fizinį prietaisą bei gautų matavimų atvaizdavimą virtualiame ekrane.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        self.escort_unit = ""
        
        # Susiejamas COM prievado pasirinkimo meniu
        self.ui.combo_escort.currentIndexChanged.connect(self._on_changed)
        
        # Priskiriami matavimo režimų mygtukai.
        # Lambda funkcijos perduoda specifinius įrenginio kodus (pvz., "F0" - V DC) į siuntimo funkciją.
        self.ui.btn_esc_vdc.clicked.connect(lambda: self.set_func("F0", "V DC"))
        self.ui.btn_esc_vac.clicked.connect(lambda: self.set_func("F1", "V AC"))
        self.ui.btn_esc_ohm.clicked.connect(lambda: self.set_func("F2", "Ω"))
        self.ui.btn_esc_adc.clicked.connect(lambda: self.set_func("F4", "A DC"))
        self.ui.btn_esc_aac.clicked.connect(lambda: self.set_func("F5", "A AC"))
        self.ui.btn_esc_diode.clicked.connect(lambda: self.set_func("F6", "V"))
        self.ui.btn_esc_hz.clicked.connect(lambda: self.set_func("F7", "Hz"))
        
        # Rankinio nuskaitymo mygtuko susiejimas
        self.ui.btn_esc_read_all.clicked.connect(self.refresh)

    def _on_changed(self):
        """
        Apdoroja COM prievado pasikeitimą išskleidžiamajame sąraše.
        Integruota apsauga nuo prievadų konfliktų: jei pasirenkamas prievadas,
        kurį jau naudoja TTi 1604, TTi ryšys yra automatiškai nutraukiamas.
        """
        port = self.ui.combo_escort.currentData()
        
        # Patikrinama, ar prievadas jau nėra užimtas kito multimetro (TTi)
        if port and port == self.ui.combo_tti.currentData():
            self.ui.combo_tti.blockSignals(True)
            self.ui.combo_tti.setCurrentIndex(0)
            self.ui.combo_tti.blockSignals(False)
            with self.mgr.lock:
                if self.mgr.tti: 
                    self.mgr.tti.close()
                    self.mgr.tti = None
                    
        # Prijungiamas arba atjungiamas Escort prietaisas
        if port: 
            self.mgr.connect_esc(port)
        else:
            with self.mgr.lock:
                if self.mgr.esc: 
                    self.mgr.esc.close()
                    self.mgr.esc = None

    def set_func(self, cmd, default_unit):
        """
        Išsiunčia matavimo režimo keitimo komandą į prietaisą.
        Naudojamas asimetrinis siuntimas (QTimer), kad neužblokuotų pagrindinės GUI gijos.
        """
        if not self.mgr.esc: 
            return self.main.log_msg("Klaida: Escort neprijungtas.")
            
        self.escort_unit = default_unit
        self.main.show_loading(f"Konfigūruojamas Escort ({default_unit})...")
        
        # Užrakinama magistralė, išsiunčiama komanda, atleidžiamas užraktas
        # ir po 500 ms (leidžiant prietaisui perjungti vidines reles) iškviečiamas momentinis nuskaitymas.
        QTimer.singleShot(100, lambda: (
            self.mgr.lock.acquire(), 
            self.mgr.esc.send_command(cmd), 
            self.mgr.lock.release(), 
            self.main.hide_loading(), 
            QTimer.singleShot(500, self.refresh)
        ))

    def refresh(self):
        """Inicijuoja duomenų nuskaitymo procedūrą su krovimo indikacija sąsajoje."""
        if not self.mgr.esc: return
        self.main.show_loading("Nuskaitomi duomenys iš Escort...")
        QTimer.singleShot(100, self._perform_refresh)

    def _perform_refresh(self):
        """
        Fiziškai nuskaito duomenis iš prietaiso per nuosekliąją magistralę,
        atnaujina virtualų LCD ekraną ir pritaiko atitinkamą spalvų stilių.
        """
        with self.mgr.lock:
            val, unit = self.mgr.esc.read_measurement()
            
            if val is not None: 
                # Jei prietaisas atsakyme negrąžina matavimo vieneto, naudojamas numatytasis iš paspausto mygtuko
                disp_u = unit if unit else self.escort_unit
                self.ui.lbl_esc_val.setText(f"{val} {disp_u}".strip())
                
                # Dinaminis stiliaus keitimas: AC/Hz atvaizduojami oranžine, DC - žalia spalva
                self.ui.lbl_esc_val.setStyleSheet(STYLE_LCD_AC if "AC" in disp_u or "Hz" in disp_u else STYLE_LCD_DC)
            else: 
                self.ui.lbl_esc_val.setText("KLAIDA")
                
        self.main.hide_loading()