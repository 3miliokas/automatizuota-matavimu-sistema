from PyQt6.QtCore import QTimer

class GenController:
    """
    Siglent SDG serijos signalų generatoriaus valdymo valdiklis.
    Apdoroja GUI elementų įvestis, konvertuoja inžinerinius vienetus į
    bazinius SI vienetus ir siunčia SCPI komandas per InstrumentManager.
    Taip pat užtikrina dvikryptę sinchronizaciją – atnaujina programos UI
    pagal fizinius prietaiso nustatymus.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr

        # UI signalų susiejimas su funkcijomis
        self.ui.combo_gen.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_apply_gen.clicked.connect(self.apply_params)
        self.ui.btn_eqphase.clicked.connect(self.apply_eqphase)
        
        # Kanalų aktyvavimo mygtukų būsenų atnaujinimas ir komandų siuntimas
        self.ui.btn_gen_ch1.toggled.connect(lambda s: (self.set_output(s, 1), self.main.update_toggle_button_style(self.ui.btn_gen_ch1, s)))
        self.ui.btn_gen_ch2.toggled.connect(lambda s: (self.set_output(s, 2), self.main.update_toggle_button_style(self.ui.btn_gen_ch2, s)))

    def _on_changed(self):
        """Apdoroja generatoriaus VISA adreso pasikeitimą išskleidžiamajame sąraše."""
        addr = self.ui.combo_gen.currentData()
        if addr: 
            self.mgr.connect_gen(addr)
        else:
            with self.mgr.lock:
                if self.mgr.gen: 
                    self.mgr.gen.close()
                    self.mgr.gen = None

    def set_output(self, state, channel):
        """Įjungia arba išjungia nurodyto kanalo signalo generavimą išvestyje."""
        if not self.mgr.gen: return
        with self.mgr.lock: 
            self.mgr.gen.set_output(state, channel)

    def apply_eqphase(self):
        """Programiškai sinchronizuoja (numeta į 0°) abiejų kanalų fazes."""
        if not self.mgr.gen: return
        with self.mgr.lock: 
            self.mgr.gen.sync_eqphase()

    def apply_params(self):
        """
        Inicijuoja signalo formavimo komandų sekos siuntimą.
        Naudoja asimetrinį atidėjimą, kad parodytų krovimo langą prieš užblokuojant giją.
        """
        if not self.mgr.gen: 
            return self.main.log_msg("Klaida: Generatorius neprijungtas.")
        
        self.main.show_loading("Siunčiami parametrai į generatorių...")
        QTimer.singleShot(100, self._perform_apply)

    def _perform_apply(self):
        """Fiziškai išsiunčia konfigūracijos parametrus į prietaisą."""
        unit = self.ui.freq_unit.currentText()
        
        # Dažnio arba periodo vienetų konvertavimas į bazinius (Hz arba s), 
        # priklausomai nuo to, kokį režimą pasirinko vartotojas.
        freq_val = self.ui.freq_in.value() * (
            {"Hz": 1, "kHz": 1e3, "MHz": 1e6}[unit] 
            if self.ui.combo_freq_type.currentIndex() == 0 
            else {"s": 1, "ms": 1e-3, "us": 1e-6}[unit]
        )
        
        f_mode = "FRQ" if self.ui.combo_freq_type.currentIndex() == 0 else "PERI"
        amp_mode = "AMP" if self.ui.combo_amp_type.currentIndex() == 0 else "HLEV"
        ch = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
        
        # Saugus prietaiso resursų užrakinimas prieš siunčiant SCPI komandas
        with self.mgr.lock:
            self.mgr.gen.apply_waveform(
                self.ui.wave_type.currentText(), 
                f_mode, 
                freq_val, 
                amp_mode, 
                self.ui.amp_in.value(), 
                self.ui.offset_in.value(), 
                self.ui.phase_in.value(), 
                self.ui.duty_in.value(), 
                self.ui.sym_in.value(), 
                self.ui.delay_in.value(), 
                self.ui.stdev_in.value(), 
                self.ui.mean_in.value(), 
                ch
            )
            
        self.main.hide_loading()

    def sync_ui(self):
        """
        Dvikryptė sinchronizacija (Polling). 
        Reguliariai apklausia generatoriaus būseną (kanalų aktyvumą, dažnį, amplitudę)
        ir atnaujina GUI elementus, jei parametrai buvo pakeisti tiesiogiai fiziniame prietaise.
        """
        if not self.mgr.lock.locked() and self.mgr.gen:
            with self.mgr.lock:
                # Laikinai išjungiamas žurnalo pildymas (logging), kad polling nešiukšlintų konsolės
                old_logger = self.mgr.gen.logger
                self.mgr.gen.logger = None
                try:
                    # 1. Atnaujinama kanalų išvesčių būsena
                    ch1 = self.mgr.gen.get_output_state(1)
                    ch2 = self.mgr.gen.get_output_state(2)
                    
                    self.ui.btn_gen_ch1.blockSignals(True)
                    self.ui.btn_gen_ch1.setChecked(ch1)
                    self.main.update_toggle_button_style(self.ui.btn_gen_ch1, ch1)
                    self.ui.btn_gen_ch1.blockSignals(False)
                    
                    self.ui.btn_gen_ch2.blockSignals(True)
                    self.ui.btn_gen_ch2.setChecked(ch2)
                    self.main.update_toggle_button_style(self.ui.btn_gen_ch2, ch2)
                    self.ui.btn_gen_ch2.blockSignals(False)
                    
                    # 2. Atnaujinami aktyvaus kanalo signalo parametrai
                    ch_sel = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
                    params = self.mgr.gen.get_waveform_params(ch_sel)
                    
                    # --- Dažnio sinchronizacija ---
                    if params and "FRQ" in params:
                        try:
                            # Pašalinami SCPI vienetų simboliai iš atsakymo
                            f_val = float(params["FRQ"].replace('HZ','').replace('V','').replace('S',''))
                            
                            # Jei vartotojas šiuo metu neveda dažnio (laukelis neturi fokuso), atnaujiname
                            if not self.ui.freq_in.hasFocus():
                                self.ui.freq_in.blockSignals(True)
                                if f_val >= 1e6: 
                                    self.ui.freq_in.setValue(f_val/1e6)
                                    self.ui.freq_unit.setCurrentText("MHz")
                                elif f_val >= 1e3: 
                                    self.ui.freq_in.setValue(f_val/1e3)
                                    self.ui.freq_unit.setCurrentText("kHz")
                                else: 
                                    self.ui.freq_in.setValue(f_val)
                                    self.ui.freq_unit.setCurrentText("Hz")
                                self.ui.freq_in.blockSignals(False)
                        except: pass
                        
                    # --- Amplitudės sinchronizacija ---
                    if params and "AMP" in params:
                        try:
                            a_val = float(params["AMP"].replace('V',''))
                            if not self.ui.amp_in.hasFocus():
                                self.ui.amp_in.blockSignals(True)
                                self.ui.amp_in.setValue(a_val)
                                self.ui.amp_in.blockSignals(False)
                        except: pass
                except: pass
                finally: 
                    # Atstatomas pirminis žurnalo (logger) objektas
                    self.mgr.gen.logger = old_logger