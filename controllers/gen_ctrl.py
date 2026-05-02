from PyQt6.QtCore import QTimer

class GenController:
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr

        self.ui.combo_gen.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_apply_gen.clicked.connect(self.apply_params)
        self.ui.btn_eqphase.clicked.connect(self.apply_eqphase)
        self.ui.btn_gen_ch1.toggled.connect(lambda s: (self.set_output(s, 1), self.main.update_toggle_button_style(self.ui.btn_gen_ch1, s)))
        self.ui.btn_gen_ch2.toggled.connect(lambda s: (self.set_output(s, 2), self.main.update_toggle_button_style(self.ui.btn_gen_ch2, s)))

    def _on_changed(self):
        addr = self.ui.combo_gen.currentData()
        if addr: self.mgr.connect_gen(addr)
        else:
            with self.mgr.lock:
                if self.mgr.gen: self.mgr.gen.close(); self.mgr.gen = None

    def set_output(self, state, channel):
        if not self.mgr.gen: return
        with self.mgr.lock: self.mgr.gen.set_output(state, channel)

    def apply_eqphase(self):
        if not self.mgr.gen: return
        with self.mgr.lock: self.mgr.gen.sync_eqphase()

    def apply_params(self):
        if not self.mgr.gen: return self.main.log_msg("Klaida: Generatorius neprijungtas.")
        self.main.show_loading("Siunčiami parametrai į generatorių...")
        QTimer.singleShot(100, self._perform_apply)

    def _perform_apply(self):
        unit = self.ui.freq_unit.currentText()
        freq_val = self.ui.freq_in.value() * ({"Hz": 1, "kHz": 1e3, "MHz": 1e6}[unit] if self.ui.combo_freq_type.currentIndex() == 0 else {"s": 1, "ms": 1e-3, "us": 1e-6}[unit])
        f_mode = "FRQ" if self.ui.combo_freq_type.currentIndex() == 0 else "PERI"
        amp_mode = "AMP" if self.ui.combo_amp_type.currentIndex() == 0 else "HLEV"
        ch = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
        
        with self.mgr.lock:
            self.mgr.gen.apply_waveform(self.ui.wave_type.currentText(), f_mode, freq_val, amp_mode, self.ui.amp_in.value(), self.ui.offset_in.value(), self.ui.phase_in.value(), self.ui.duty_in.value(), self.ui.sym_in.value(), self.ui.delay_in.value(), self.ui.stdev_in.value(), self.ui.mean_in.value(), ch)
        self.main.hide_loading()

    def sync_ui(self):
        if not self.mgr.lock.locked() and self.mgr.gen:
            with self.mgr.lock:
                old_logger = self.mgr.gen.logger
                self.mgr.gen.logger = None
                try:
                    ch1 = self.mgr.gen.get_output_state(1)
                    ch2 = self.mgr.gen.get_output_state(2)
                    self.ui.btn_gen_ch1.blockSignals(True); self.ui.btn_gen_ch1.setChecked(ch1); self.main.update_toggle_button_style(self.ui.btn_gen_ch1, ch1); self.ui.btn_gen_ch1.blockSignals(False)
                    self.ui.btn_gen_ch2.blockSignals(True); self.ui.btn_gen_ch2.setChecked(ch2); self.main.update_toggle_button_style(self.ui.btn_gen_ch2, ch2); self.ui.btn_gen_ch2.blockSignals(False)
                    
                    ch_sel = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
                    params = self.mgr.gen.get_waveform_params(ch_sel)
                    
                    if params and "FRQ" in params:
                        try:
                            f_val = float(params["FRQ"].replace('HZ','').replace('V','').replace('S',''))
                            if not self.ui.freq_in.hasFocus():
                                self.ui.freq_in.blockSignals(True)
                                if f_val >= 1e6: self.ui.freq_in.setValue(f_val/1e6); self.ui.freq_unit.setCurrentText("MHz")
                                elif f_val >= 1e3: self.ui.freq_in.setValue(f_val/1e3); self.ui.freq_unit.setCurrentText("kHz")
                                else: self.ui.freq_in.setValue(f_val); self.ui.freq_unit.setCurrentText("Hz")
                                self.ui.freq_in.blockSignals(False)
                        except: pass
                        
                    if params and "AMP" in params:
                        try:
                            a_val = float(params["AMP"].replace('V',''))
                            if not self.ui.amp_in.hasFocus():
                                self.ui.amp_in.blockSignals(True)
                                self.ui.amp_in.setValue(a_val)
                                self.ui.amp_in.blockSignals(False)
                        except: pass
                except: pass
                finally: self.mgr.gen.logger = old_logger