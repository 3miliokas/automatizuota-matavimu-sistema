import numpy as np
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QApplication
from PyQt6.QtCore import QTimer
from gui.theme import STYLE_SUCCESS, STYLE_DANGER

class OscController:
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_plot)

        self.ui.combo_osc.currentIndexChanged.connect(self._on_changed)
        self.ui.btn_auto.clicked.connect(self.trigger_autoscale)
        self.ui.btn_run.toggled.connect(self.toggle_run_stop)
        
        self.ui.btn_osc_ch1.toggled.connect(lambda s: (self.set_display(s, 1), self.main.update_toggle_button_style(self.ui.btn_osc_ch1, s), self.main.curves[1].setVisible(s)))
        self.ui.btn_osc_ch2.toggled.connect(lambda s: (self.set_display(s, 2), self.main.update_toggle_button_style(self.ui.btn_osc_ch2, s), self.main.curves[2].setVisible(s)))
        self.ui.btn_osc_ch3.toggled.connect(lambda s: (self.set_display(s, 3), self.main.update_toggle_button_style(self.ui.btn_osc_ch3, s), self.main.curves[3].setVisible(s)))
        self.ui.btn_osc_ch4.toggled.connect(lambda s: (self.set_display(s, 4), self.main.update_toggle_button_style(self.ui.btn_osc_ch4, s), self.main.curves[4].setVisible(s)))
        
        self.ui.btn_meas_all.clicked.connect(self.fetch_measurements)
        self.ui.btn_osc_screenshot.clicked.connect(self.save_screenshot)
        self.ui.btn_copy_meas.clicked.connect(self.copy_measurements)
        self.ui.btn_stream.toggled.connect(self.toggle_stream)
        self.ui.btn_calc_fft.clicked.connect(self.calculate_fft)

    def _on_changed(self):
        addr = self.ui.combo_osc.currentData()
        if addr: self.mgr.connect_osc(addr)
        else:
            with self.mgr.lock:
                if self.mgr.osc: self.mgr.osc.close(); self.mgr.osc = None

    def trigger_autoscale(self):
        if not self.mgr.osc: return
        with self.mgr.lock: self.mgr.osc.auto_scale()
        self.ui.graph_widget.enableAutoRange()

    def toggle_run_stop(self, state):
        if not self.mgr.osc: return
        with self.mgr.lock: self.mgr.osc.run() if state else self.mgr.osc.stop()
        self.main.update_run_stop_btn(self.ui.btn_run, state)

    def set_display(self, state, channel):
        if not self.mgr.osc: return
        with self.mgr.lock: self.mgr.osc.set_channel_display(state, channel)

    def fetch_measurements(self):
        if not self.mgr.osc: return
        self.main.show_loading("Nuskaitomi parametrai iš oscilografo...")
        QTimer.singleShot(100, self._perform_fetch)

    def _perform_fetch(self):
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.stream_timer.stop()
        
        ch = self.ui.combo_meas_ch.currentIndex() + 1
        params = [("VPP", "Vpp", "V"), ("VMAX", "Vmax", "V"), ("VMIN", "Vmin", "V"), ("VAMP", "Vamp", "V"),
                  ("VTOP", "Vtop", "V"), ("VBAS", "Vbase", "V"), ("VAVG", "Vavg", "V"), ("VRMS", "Vrms", "V"),
                  ("OVER", "Overshoot", "%"), ("PRE", "Preshoot", "%"), ("FREQ", "Freq", "Hz"), ("PER", "Period", "s"),
                  ("RTIM", "Rise Time", "s"), ("FTIM", "Fall Time", "s"), ("PWID", "Pulse (+)", "s"), ("NWID", "Pulse (-)", "s"),
                  ("PDUT", "Duty (+)", "%"), ("NDUT", "Duty (-)", "%")]
        with self.mgr.lock:
            for i, (cmd, name, unit) in enumerate(params):
                val = self.mgr.osc.get_measure(cmd, channel=ch)
                val_str = f"{val:.4e} {unit}" if (val is not None and val < 1e15) else "-"
                self.ui.table_meas.setItem(i, 0, QTableWidgetItem(name))
                self.ui.table_meas.setItem(i, 1, QTableWidgetItem(val_str))
        self.main.hide_loading()

    def copy_measurements(self):
        text = "Parametras\tReikšmė\n"
        for i in range(self.ui.table_meas.rowCount()):
            item0 = self.ui.table_meas.item(i, 0)
            item1 = self.ui.table_meas.item(i, 1)
            if item0 and item1 and item1.text() != "-": text += f"{item0.text()}\t{item1.text()}\n"
        QApplication.clipboard().setText(text)
        self.main.log_msg("Matavimų lentelė nukopijuota.")

    def save_screenshot(self):
        if not self.mgr.osc: return
        fn, _ = QFileDialog.getSaveFileName(self.main, "Išsaugoti", "", "BMP Image (*.bmp)")
        if not fn: return
        self.main.show_loading("Traukiama ekrano kopija...")
        QTimer.singleShot(100, lambda: (self.mgr.lock.acquire(), open(fn, 'wb').write(self.mgr.osc.get_screenshot() or b''), self.mgr.lock.release(), self.main.hide_loading()))

    def calculate_fft(self):
        if not self.mgr.osc: return
        self.main.show_loading("Skaičiuojama FFT...")
        QTimer.singleShot(100, self._perform_fft)

    def _perform_fft(self):
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.ui.btn_stream.setChecked(False)
        self.ui.graph_tabs.setCurrentIndex(3) 
        with self.mgr.lock: t, v = self.mgr.osc.get_waveform_data(channel=1)
        if len(t) > 1:
            n = len(v); yf = np.fft.fft(v); xf = np.fft.fftfreq(n, d=(t[1]-t[0])); half_n = n // 2
            self.main.fft_x = xf[:half_n]; self.main.fft_y = 2.0 / n * np.abs(yf[:half_n]); self.main.fft_y[0] = 0
            self.main.fft_line.setData(self.main.fft_x, self.main.fft_y)
            peak_idx = np.argmax(self.main.fft_y)
            self.ui.lbl_fft_peak.setText(f"Pikas: {self.main.fft_x[peak_idx]:.2e} Hz ({self.main.fft_y[peak_idx]:.3f} V)")
        self.main.hide_loading()
        if was_streaming: self.ui.btn_stream.setChecked(True)

    def toggle_stream(self, state):
        if state:
            if not self.mgr.osc:
                self.main.log_msg("Nepasirinktas oscilografas.")
                self.ui.btn_stream.blockSignals(True); self.ui.btn_stream.setChecked(False); self.ui.btn_stream.blockSignals(False)
                return
            self.ui.graph_tabs.setCurrentIndex(0)
            self.ui.btn_stream.setText("STOP Atvaizdavimą"); self.ui.btn_stream.setStyleSheet(STYLE_SUCCESS)
            self.stream_timer.start(2000)
        else:
            self.stream_timer.stop()
            self.ui.btn_stream.setText("START Atvaizdavimą"); self.ui.btn_stream.setStyleSheet(STYLE_DANGER)

    def update_plot(self):
        if not self.mgr.osc: return
        if not self.mgr.lock.locked():
            with self.mgr.lock:
                old_logger = self.mgr.osc.logger; self.mgr.osc.logger = None  
                try:
                    active = [i for i, btn in enumerate([self.ui.btn_osc_ch1, self.ui.btn_osc_ch2, self.ui.btn_osc_ch3, self.ui.btn_osc_ch4], 1) if btn.isChecked()]
                    for ch in range(1, 5):
                        if ch in active:
                            t, v = self.mgr.osc.get_waveform_data(channel=ch)
                            if t is not None and len(t) > 0: self.main.curves[ch].setData(t, v); self.main.curves[ch].setVisible(True)
                        else:
                            self.main.curves[ch].setData([], []); self.main.curves[ch].setVisible(False)
                finally: self.mgr.osc.logger = old_logger

    def sync_ui(self):
        if not self.mgr.lock.locked() and self.mgr.osc:
            with self.mgr.lock:
                old_logger = self.mgr.osc.logger; self.mgr.osc.logger = None
                try:
                    states = [self.mgr.osc.get_channel_state(i) for i in range(1, 5)]
                    run_st = self.mgr.osc.get_run_state()
                    for i, btn in enumerate([self.ui.btn_osc_ch1, self.ui.btn_osc_ch2, self.ui.btn_osc_ch3, self.ui.btn_osc_ch4]):
                        btn.blockSignals(True); btn.setChecked(states[i]); self.main.update_toggle_button_style(btn, states[i]); btn.blockSignals(False)
                        self.main.curves[i+1].setVisible(states[i])
                    self.ui.btn_run.blockSignals(True); self.ui.btn_run.setChecked(run_st); self.main.update_run_stop_btn(self.ui.btn_run, run_st); self.ui.btn_run.blockSignals(False)
                except: pass
                finally: self.mgr.osc.logger = old_logger