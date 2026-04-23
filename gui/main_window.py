import os
import csv
import math
import re
import time
from datetime import datetime
import numpy as np

import pyvisa
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QTableWidgetItem
from PyQt6.QtCore import QTimer

from gui.ui_layout import Ui_MainWindow
from core.workers import BodeSweepWorker, DataLoggerWorker

from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)

        self.x_data, self.y_data = [], []
        self.data_line = self.ui.graph_widget.plot(self.x_data, self.y_data, pen='y')
        
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_plot_from_rigol)
        
        self.bode_worker = None
        self.bode_freqs = []; self.bode_x = []; self.bode_y = []
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')

        self.log_worker = None
        self.log_x = []; self.log_y = []
        self.log_line = self.ui.log_graph.plot(self.log_x, self.log_y, pen='g')

        self.fft_x = []; self.fft_y = []
        self.fft_line = self.ui.fft_graph.plot(self.fft_x, self.fft_y, pen='m', fillLevel=0, brush=(156,39,176,50))

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.poll_hardware)

        self.connect_signals()

    def connect_signals(self):
        self.ui.btn_scan.clicked.connect(self.scan_devices)
        self.ui.btn_generate_pdf.clicked.connect(self.generate_pdf_report)
        
        self.ui.btn_apply_gen.clicked.connect(self.apply_generator)
        self.ui.btn_gen_ch1.toggled.connect(lambda state: self.set_gen_output(state, 1))
        self.ui.btn_gen_ch2.toggled.connect(lambda state: self.set_gen_output(state, 2))
        self.ui.gen_ch_select.currentIndexChanged.connect(self.sync_generator_params_to_ui)
        
        self.ui.btn_auto.clicked.connect(self.trigger_autoscale)
        self.ui.btn_run.toggled.connect(self.toggle_osc_run_stop)
        self.ui.btn_osc_ch1.toggled.connect(lambda state: self.set_osc_display(state, 1))
        self.ui.btn_osc_ch2.toggled.connect(lambda state: self.set_osc_display(state, 2))
        self.ui.btn_osc_ch3.toggled.connect(lambda state: self.set_osc_display(state, 3))
        self.ui.btn_osc_ch4.toggled.connect(lambda state: self.set_osc_display(state, 4))
        self.ui.btn_meas_all.clicked.connect(self.fetch_all_measurements)
        
        self.ui.btn_start_stream.clicked.connect(self.start_stream)
        self.ui.btn_stop_stream.clicked.connect(self.stop_stream)
        self.ui.btn_export.clicked.connect(self.export_csv)
        
        self.ui.btn_tti_operate.clicked.connect(lambda: self.send_tti_cmd("OPERATE"))
        self.ui.btn_tti_up.clicked.connect(lambda: self.send_tti_cmd("UP"))
        self.ui.btn_tti_down.clicked.connect(lambda: self.send_tti_cmd("DOWN"))
        self.ui.btn_tti_auto.clicked.connect(lambda: self.send_tti_cmd("AUTO"))

        self.ui.btn_tti_v.clicked.connect(lambda: self.send_tti_cmd("V"))
        self.ui.btn_tti_a.clicked.connect(lambda: self.send_tti_cmd("A"))
        self.ui.btn_tti_ma.clicked.connect(lambda: self.send_tti_cmd("mA"))
        self.ui.btn_tti_mv.clicked.connect(lambda: self.send_tti_cmd("mV"))
        self.ui.btn_tti_dc.clicked.connect(lambda: self.send_tti_cmd("DC"))
        self.ui.btn_tti_ac.clicked.connect(lambda: self.send_tti_cmd("AC"))
        self.ui.btn_tti_ohm.clicked.connect(lambda: self.send_tti_cmd("OHM"))
        self.ui.btn_tti_hz.clicked.connect(lambda: self.send_tti_cmd("FREQ"))

        self.ui.btn_tti_diode.clicked.connect(lambda: self.send_tti_shift_cmd("V"))
        self.ui.btn_tti_minmax.clicked.connect(lambda: self.send_tti_shift_cmd("A"))
        self.ui.btn_tti_hold.clicked.connect(lambda: self.send_tti_shift_cmd("mA"))
        self.ui.btn_tti_thold.clicked.connect(lambda: self.send_tti_shift_cmd("mV"))
        self.ui.btn_tti_null.clicked.connect(lambda: self.send_tti_shift_cmd("DC"))
        self.ui.btn_tti_reset.clicked.connect(lambda: self.send_tti_shift_cmd("AC"))
        self.ui.btn_tti_cont.clicked.connect(lambda: self.send_tti_shift_cmd("OHM"))
        self.ui.btn_tti_review.clicked.connect(lambda: self.send_tti_shift_cmd("FREQ"))

        self.ui.btn_tti_refresh.clicked.connect(self.refresh_tti)
        
        self.ui.btn_esc_read.clicked.connect(lambda: self.fetch_escort("V"))
        
        self.ui.btn_start_bode.clicked.connect(self.start_bode_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_bode_sweep)
        self.ui.btn_export_bode.clicked.connect(self.export_bode_csv)
        self.ui.bode_device.currentIndexChanged.connect(self.toggle_bode_channels)
        
        self.ui.btn_start_log.clicked.connect(self.start_logging)
        self.ui.btn_stop_log.clicked.connect(self.stop_logging)
        self.ui.btn_calc_fft.clicked.connect(self.calculate_fft)

        self.toggle_bode_channels()

    def log_msg(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.log_console.append(f"[{timestamp}] {text}")
        self.ui.log_console.verticalScrollBar().setValue(self.ui.log_console.verticalScrollBar().maximum())

    def format_eng(self, val, unit="V"):
        if val is None or val > 1e15: return "N/A" 
        if val == 0: return f"0.00 {unit}"
        abs_val = abs(val)
        if abs_val >= 1e9: return f"{val/1e9:.2f} G{unit}"
        if abs_val >= 1e6: return f"{val/1e6:.2f} M{unit}"
        if abs_val >= 1e3: return f"{val/1e3:.2f} k{unit}"
        if abs_val >= 1: return f"{val:.2f} {unit}"
        if abs_val >= 1e-3: return f"{val*1e3:.2f} m{unit}"
        if abs_val >= 1e-6: return f"{val*1e6:.2f} µ{unit}"
        if abs_val >= 1e-9: return f"{val*1e9:.2f} n{unit}"
        return f"{val:.2e} {unit}"

    def poll_hardware(self):
        if self.stream_timer.isActive(): return
        if self.bode_worker and self.bode_worker.isRunning(): return
        if self.log_worker and self.log_worker.isRunning(): return

        gen_addr = self.ui.combo_gen.currentData()
        if gen_addr:
            try:
                gen = SiglentSDG(gen_addr)
                ch1 = gen.get_output_state(1)
                ch2 = gen.get_output_state(2)
                gen.close()
                self.ui.btn_gen_ch1.blockSignals(True); self.ui.btn_gen_ch1.setChecked(ch1); self.ui.btn_gen_ch1.blockSignals(False)
                self.ui.btn_gen_ch2.blockSignals(True); self.ui.btn_gen_ch2.setChecked(ch2); self.ui.btn_gen_ch2.blockSignals(False)
            except: pass

        osc_addr = self.ui.combo_osc.currentData()
        if osc_addr:
            try:
                osc = RigolMSO(osc_addr)
                ch1 = osc.get_channel_state(1)
                ch2 = osc.get_channel_state(2)
                ch3 = osc.get_channel_state(3)
                ch4 = osc.get_channel_state(4)
                run_st = osc.get_run_state()
                osc.close()
                self.ui.btn_osc_ch1.blockSignals(True); self.ui.btn_osc_ch1.setChecked(ch1); self.ui.btn_osc_ch1.blockSignals(False)
                self.ui.btn_osc_ch2.blockSignals(True); self.ui.btn_osc_ch2.setChecked(ch2); self.ui.btn_osc_ch2.blockSignals(False)
                self.ui.btn_osc_ch3.blockSignals(True); self.ui.btn_osc_ch3.setChecked(ch3); self.ui.btn_osc_ch3.blockSignals(False)
                self.ui.btn_osc_ch4.blockSignals(True); self.ui.btn_osc_ch4.setChecked(ch4); self.ui.btn_osc_ch4.blockSignals(False)
                self.ui.btn_run.blockSignals(True); self.ui.btn_run.setChecked(run_st); self.ui.btn_run.blockSignals(False)
            except: pass

    def scan_devices(self):
        self.ui.combo_gen.clear(); self.ui.combo_osc.clear(); self.ui.combo_tti.clear(); self.ui.combo_escort.clear()
        self.log_msg("Skenuojama su automatiniu parinkimu...")
        rm = pyvisa.ResourceManager()
        
        gen_found, osc_found = False, False
        for addr in rm.list_resources():
            try:
                inst = rm.open_resource(addr)
                inst.timeout = 2000
                idn = inst.query("*IDN?").strip()
                inst.close()
                name = idn.split(',')[1] if len(idn.split(',')) > 1 else idn
                item_text = f"{name} [{addr}]"
                
                self.ui.combo_gen.addItem(item_text, addr)
                self.ui.combo_osc.addItem(item_text, addr)
                
                if "SDG" in idn.upper() and not gen_found:
                    self.ui.combo_gen.setCurrentIndex(self.ui.combo_gen.count() - 1)
                    gen_found = True
                elif ("DS1" in idn.upper() or "MSO" in idn.upper()) and not osc_found:
                    self.ui.combo_osc.setCurrentIndex(self.ui.combo_osc.count() - 1)
                    osc_found = True
            except Exception: pass
            
        for port in serial.tools.list_ports.comports():
            info = f"{port.device} - {port.description}"
            self.ui.combo_tti.addItem(info, port.device)
            self.ui.combo_escort.addItem(info, port.device)
            
            try:
                tti = TTi1604(port.device)
                tti.send_command("OPERATE")
                tti.close()
            except:
                pass
            
        self.log_msg("Skenavimas baigtas. Aktyvuojama būsenų sinchronizacija.")
        self.sync_timer.start(2000)
        self.sync_generator_params_to_ui()

    def sync_generator_params_to_ui(self):
        addr = self.ui.combo_gen.currentData()
        if not addr: return
        try:
            gen = SiglentSDG(addr)
            ch = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
            resp = gen.get_waveform_params(ch)
            gen.close()
            
            if not resp: return
            
            clean_str = resp.replace(f"C{ch}:BSWV ", "").strip()
            parts = clean_str.split(',')
            params = {}
            for i in range(0, len(parts)-1, 2):
                params[parts[i].upper()] = parts[i+1]

            self.ui.wave_type.blockSignals(True)
            self.ui.freq_in.blockSignals(True)
            self.ui.amp_in.blockSignals(True)
            self.ui.offset_in.blockSignals(True)
            self.ui.phase_in.blockSignals(True)
            self.ui.duty_in.blockSignals(True)
            self.ui.sym_in.blockSignals(True)

            if "WVTP" in params:
                wt = params["WVTP"].capitalize()
                idx = self.ui.wave_type.findText(wt)
                if idx >= 0: self.ui.wave_type.setCurrentIndex(idx)

            if "FRQ" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["FRQ"])
                freq_hz = float(val_str)
                unit_m = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
                curr_unit = self.ui.freq_unit.currentText()
                self.ui.freq_in.setValue(freq_hz / unit_m.get(curr_unit, 1))

            if "AMP" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["AMP"])
                self.ui.amp_in.setValue(float(val_str))

            if "OFST" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["OFST"])
                self.ui.offset_in.setValue(float(val_str))
                
            if "PHSE" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["PHSE"])
                self.ui.phase_in.setValue(float(val_str))
                
            if "DUTY" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["DUTY"])
                self.ui.duty_in.setValue(float(val_str))
                
            if "SYM" in params:
                val_str = re.sub(r'[a-zA-Z]', '', params["SYM"])
                self.ui.sym_in.setValue(float(val_str))

            self.ui.wave_type.blockSignals(False)
            self.ui.freq_in.blockSignals(False)
            self.ui.amp_in.blockSignals(False)
            self.ui.offset_in.blockSignals(False)
            self.ui.phase_in.blockSignals(False)
            self.ui.duty_in.blockSignals(False)
            self.ui.sym_in.blockSignals(False)
        except Exception as e:
            pass

    def set_gen_output(self, state, channel):
        addr = self.ui.combo_gen.currentData()
        if not addr: return
        try:
            gen = SiglentSDG(addr)
            gen.set_output(state, channel)
            gen.close()
            self.log_msg(f"Generatoriaus CH{channel} {'ON' if state else 'OFF'}")
        except Exception as e:
            self.log_msg(f"Klaida: {e}")

    def apply_generator(self):
        addr = self.ui.combo_gen.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas generatorius.")
        try:
            m = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
            freq_hz = self.ui.freq_in.value() * m[self.ui.freq_unit.currentText()]
            ch = 1 if self.ui.gen_ch_select.currentIndex() == 0 else 2
            
            gen = SiglentSDG(addr)
            gen.apply_waveform(self.ui.wave_type.currentText(), freq_hz, 
                               self.ui.amp_in.value(), self.ui.offset_in.value(),
                               self.ui.phase_in.value(), self.ui.duty_in.value(), self.ui.sym_in.value(), channel=ch)
            gen.close()
            self.log_msg(f"Generatoriaus parametrai išsiųsti į CH{ch}.")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def set_osc_display(self, state, channel):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.set_channel_display(state, channel)
            osc.close()
            self.log_msg(f"Oscilografo CH{channel} rodymas {'ON' if state else 'OFF'}")
        except Exception as e:
            self.log_msg(f"Klaida: {e}")

    def trigger_autoscale(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.auto_scale()
            osc.close()
            self.ui.graph_widget.enableAutoRange()
            self.log_msg("Iškviestas oscilografo Auto-Scale.")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def toggle_osc_run_stop(self, state):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.run() if state else osc.stop()
            osc.close()
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def fetch_all_measurements(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.stream_timer.stop()
        
        ch = self.ui.combo_meas_ch.currentIndex() + 1
        
        try:
            osc = RigolMSO(addr)
            
            params = [
                ("VPP", "Vpp", "V"), ("VMAX", "Vmax", "V"), ("VMIN", "Vmin", "V"),
                ("VAMP", "Vamp", "V"), ("VTOP", "Vtop", "V"), ("VBAS", "Vbase", "V"),
                ("VAVG", "Vavg", "V"), ("VRMS", "Vrms", "V"), 
                ("OVER", "Overshoot", "%"), ("PRES", "Preshoot", "%"),
                ("FREQ", "Freq", "Hz"), ("PER", "Period", "s"),
                ("RIS", "Rise Time", "s"), ("FALL", "Fall Time", "s"),
                ("PWID", "Pos Width", "s"), ("NWID", "Neg Width", "s"),
                ("PDUT", "Pos Duty", "%"), ("NDUT", "Neg Duty", "%")
            ]
            
            self.ui.table_meas.setRowCount(len(params))
            for i, (scpi_cmd, name, unit) in enumerate(params):
                val = osc.get_measure(scpi_cmd, channel=ch)
                if val is not None and val < 1e15:
                    val_str = f"{val:.4e} {unit}"
                else:
                    val_str = "-"
                
                self.ui.table_meas.setItem(i, 0, QTableWidgetItem(name))
                self.ui.table_meas.setItem(i, 1, QTableWidgetItem(val_str))
            
            osc.close()
            self.log_msg(f"Aparatūriniai matavimai atnaujinti kanalui CH{ch}.")
        except Exception as e: 
            self.log_msg(f"Klaida prisijungiant: {e}")
            
        if was_streaming: self.stream_timer.start(500)

    def start_stream(self):
        if not self.ui.combo_osc.currentData(): return self.log_msg("Nepasirinktas oscilografas.")
        self.ui.graph_tabs.setCurrentIndex(0) 
        self.stream_timer.start(500) 
        self.log_msg("Gyvas atvaizdavimas pradėtas.")

    def stop_stream(self):
        self.stream_timer.stop()
        self.log_msg("Gyvas atvaizdavimas sustabdytas.")

    def update_plot_from_rigol(self):
        addr = self.ui.combo_osc.currentData()
        try:
            osc = RigolMSO(addr)
            t, v = osc.get_waveform_data(channel=1)
            osc.close()
            self.x_data, self.y_data = t, v
            self.data_line.setData(self.x_data, self.y_data)
        except: pass

    def export_csv(self):
        if not self.x_data: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Oscilogramą", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Time", "Voltage"])
                for x, y in zip(self.x_data, self.y_data): w.writerow([f"{x:.10e}", f"{y:.10e}"])

    def send_tti_cmd(self, cmd):
        port = self.ui.combo_tti.currentData()
        if not port: return
        try:
            tti = TTi1604(port)
            tti.send_command(cmd)
            tti.close()
            self.log_msg(f"TTi: Išsiųsta komanda {cmd}")
            QTimer.singleShot(400, self.refresh_tti)
        except Exception as e:
            self.log_msg(f"TTi Klaida: {e}")

    def send_tti_shift_cmd(self, primary_cmd):
        port = self.ui.combo_tti.currentData()
        if not port: return
        try:
            tti = TTi1604(port)
            tti.send_command("SHIFT")
            time.sleep(0.2)
            tti.send_command(primary_cmd)
            tti.close()
            self.log_msg(f"TTi: Išsiųsta komanda SHIFT + {primary_cmd}")
            QTimer.singleShot(400, self.refresh_tti)
        except Exception as e:
            self.log_msg(f"TTi Klaida: {e}")

    def refresh_tti(self):
        port = self.ui.combo_tti.currentData()
        if not port: return
        try:
            tti = TTi1604(port)
            val, unit, mode = tti.get_reading()
            tti.close()

            if val is not None:
                self.ui.lbl_tti_val.setText(f"{val:.4f} {unit} {mode}")
                if "AC" in mode:
                    self.ui.lbl_tti_val.setStyleSheet(self.ui.tti_ac_style)
                else:
                    self.ui.lbl_tti_val.setStyleSheet(self.ui.tti_dc_style)
            else:
                self.ui.lbl_tti_val.setText("KLAIDA")
        except Exception as e:
            self.log_msg(f"TTi Klaida: {e}")

    def fetch_escort(self, mode):
        port = self.ui.combo_escort.currentData()
        if not port: return
        try:
            escort = Escort3136A(port)
            val = escort.get_voltage_dc() if mode == "V" else escort.get_current_dc()
            unit = "V" if mode == "V" else "A"
            escort.close()
            if val is not None: 
                self.ui.lbl_esc_val.setText(f"{val:.4f} {unit} DC =")
            else:
                self.ui.lbl_esc_val.setText("KLAIDA")
        except Exception as e: 
            self.log_msg(f"Klaida Escort: {e}")
            self.ui.lbl_esc_val.setText("KLAIDA")

    def toggle_bode_channels(self):
        is_osc = self.ui.bode_device.currentIndex() == 0
        self.ui.bode_osc_ch.setVisible(is_osc)
        self.ui.lbl_bode_osc_ch.setVisible(is_osc)

    def start_bode_sweep(self):
        gen_addr = self.ui.combo_gen.currentData()
        dev_idx = self.ui.bode_device.currentIndex()
        meas_addr = self.ui.combo_osc.currentData() if dev_idx == 0 else (self.ui.combo_tti.currentData() if dev_idx == 1 else self.ui.combo_escort.currentData())
        if not gen_addr or not meas_addr: return self.log_msg("Klaida nustatant prietaisus!")
        
        self.ui.graph_tabs.setCurrentIndex(1)
        if self.stream_timer.isActive(): self.stream_timer.stop()
        self.bode_freqs.clear(); self.bode_x.clear(); self.bode_y.clear(); self.bode_line.setData(self.bode_x, self.bode_y)
        self.ui.bode_progress.setValue(0); self.ui.btn_start_bode.setEnabled(False)
        
        gen_ch = self.ui.bode_gen_ch.currentIndex() + 1
        osc_ch = self.ui.bode_osc_ch.currentIndex() + 1
        
        self.bode_worker = BodeSweepWorker(gen_addr, dev_idx, meas_addr, self.ui.bode_start_f.value(), self.ui.bode_stop_f.value(), self.ui.bode_points.value(), self.ui.bode_amp.value(), gen_ch, osc_ch)
        self.bode_worker.data_point.connect(self.on_bode_data)
        self.bode_worker.progress.connect(self.ui.bode_progress.setValue)
        self.bode_worker.finished.connect(self.on_bode_finished)
        self.bode_worker.error.connect(lambda e: self.log_msg(f"Klaida: {e}"))
        self.bode_worker.start()

    def on_bode_data(self, freq, val):
        v_in = self.ui.bode_amp.value()
        if val <= 0: val = 1e-6
        db = 20 * math.log10(val / v_in)
        self.bode_freqs.append(freq); self.bode_x.append(math.log10(freq)); self.bode_y.append(db)
        self.bode_line.setData(self.bode_x, self.bode_y)

    def stop_bode_sweep(self):
        if self.bode_worker and self.bode_worker.isRunning(): self.bode_worker.is_running = False

    def on_bode_finished(self):
        self.ui.btn_start_bode.setEnabled(True)
        self.log_msg("Bode Plot baigtas.")

    def export_bode_csv(self):
        if not self.bode_freqs: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Frequency_Hz", "Gain_dB"])
                for f_hz, db in zip(self.bode_freqs, self.bode_y): w.writerow([f"{f_hz:.2f}", f"{db:.4f}"])

    def calculate_fft(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas oscilografas FFT.")
        was_streaming = self.stream_timer.isActive()
        if was_streaming: self.stream_timer.stop()
        self.ui.graph_tabs.setCurrentIndex(3) 
        try:
            osc = RigolMSO(addr)
            t, v = osc.get_waveform_data(channel=1)
            osc.close()
            if len(t) < 2: raise ValueError("Nepakanka taškų.")
            dt = t[1] - t[0]
            if dt <= 0: raise ValueError("Klaidingas laiko intervalas.")
            
            n = len(v)
            yf = np.fft.fft(v)
            xf = np.fft.fftfreq(n, d=dt)
            half_n = n // 2
            
            self.fft_x = xf[:half_n]
            self.fft_y = 2.0 / n * np.abs(yf[:half_n])
            self.fft_y[0] = 0
            self.fft_line.setData(self.fft_x, self.fft_y)
            
            peak_idx = np.argmax(self.fft_y)
            peak_freq = self.fft_x[peak_idx]
            self.ui.lbl_fft_peak.setText(f"Pikas: {peak_freq:.2e} Hz ({self.fft_y[peak_idx]:.3f} V)")
            self.log_msg("FFT atliktas.")
        except Exception as e: self.log_msg(f"FFT Klaida: {e}")
        if was_streaming: self.stream_timer.start(500)

    def start_logging(self):
        dev_idx = self.ui.log_device.currentIndex()
        addr = self.ui.combo_tti.currentData() if dev_idx == 0 else self.ui.combo_escort.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas prietaisas.")
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti žurnalą", "log.csv", "CSV (*.csv)")
        if not fn: return
        self.ui.graph_tabs.setCurrentIndex(2)
        self.log_x.clear(); self.log_y.clear(); self.log_line.setData(self.log_x, self.log_y)
        self.ui.btn_start_log.setEnabled(False)
        self.log_worker = DataLoggerWorker(dev_idx, addr, self.ui.log_mode.currentIndex(), self.ui.log_interval.value(), self.ui.log_duration.value(), fn)
        self.log_worker.data_point.connect(self.on_log_data)
        self.log_worker.finished.connect(self.on_log_finished)
        self.log_worker.error.connect(lambda e: self.log_msg(f"Klaida: {e}"))
        self.log_worker.start()
        self.log_msg("Registravimas pradėtas.")

    def on_log_data(self, t, val):
        self.log_x.append(t); self.log_y.append(val); self.log_line.setData(self.log_x, self.log_y)
        unit = "V" if self.ui.log_mode.currentIndex() == 0 else "A"
        self.ui.lbl_log_current.setText(f"Reikšmė: {val:.4f} {unit}")

    def stop_logging(self):
        if self.log_worker and self.log_worker.isRunning(): self.log_worker.is_running = False

    def on_log_finished(self):
        self.ui.btn_start_log.setEnabled(True)
        self.log_msg("Registravimas sustabdytas.")

    def generate_pdf_report(self):
        try:
            from fpdf import FPDF
            import pyqtgraph.exporters
        except ImportError:
            return self.log_msg("Trūksta 'fpdf' bibliotekos.")

        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti PDF", "matavimu_protokolas.pdf", "PDF (*.pdf)")
        if not fn: return

        self.log_msg("Generuojamas PDF protokolas...")
        
        def sanitize(text_str):
            rep = {'ą':'a', 'č':'c', 'ę':'e', 'ė':'e', 'į':'i', 'š':'s', 'ų':'u', 'ū':'u', 'ž':'z',
                   'Ą':'A', 'Č':'C', 'Ę':'E', 'Ė':'E', 'Į':'I', 'Š':'S', 'Ų':'U', 'Ū':'U', 'Ž':'Z'}
            for lt, en in rep.items(): 
                text_str = text_str.replace(lt, en)
            return text_str

        try:
            pdf = FPDF()
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=sanitize("Automatizuotu Matavimu Protokolas"), ln=True, align='C')
            
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=sanitize(f"Data ir laikas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
            pdf.cell(200, 10, txt=sanitize(f"Bandomo prietaiso Serijos Nr.: {self.ui.input_serial.text()}"), ln=True)
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=sanitize("1. Generatoriaus Nustatymai (SDG):"), ln=True)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 8, txt=sanitize(f"Tipas: {self.ui.wave_type.currentText()}"), ln=True)
            pdf.cell(200, 8, txt=sanitize(f"Daznis: {self.ui.freq_in.value()} {self.ui.freq_unit.currentText()}"), ln=True)
            pdf.cell(200, 8, txt=sanitize(f"Amplitude: {self.ui.amp_in.value()} Vpp"), ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=sanitize("2. Multimetru Matavimai:"), ln=True)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 8, txt=sanitize(f"TTi 1604: {self.ui.lbl_tti_val.text()}"), ln=True)
            pdf.cell(200, 8, txt=sanitize(f"Escort 3136A: {self.ui.lbl_esc_val.text()}"), ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=sanitize("3. Oscilograma:"), ln=True)
            temp_img = "temp_plot.png"
            exporter = pyqtgraph.exporters.ImageExporter(self.ui.graph_widget.scene())
            exporter.export(temp_img)
            pdf.image(temp_img, x=10, w=190)
            os.remove(temp_img)

            if len(self.bode_x) > 0:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=sanitize("4. Amplitudes-Daznio Charakteristika (Bode):"), ln=True)
                temp_bode = "temp_bode.png"
                exporter_bode = pyqtgraph.exporters.ImageExporter(self.ui.bode_graph.scene())
                exporter_bode.export(temp_bode)
                pdf.image(temp_bode, x=10, w=190)
                os.remove(temp_bode)

            if len(self.log_x) > 0:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=sanitize("5. Ilgalaikio Registravimo Grafikas (Logger):"), ln=True)
                temp_log = "temp_log.png"
                exporter_log = pyqtgraph.exporters.ImageExporter(self.ui.log_graph.scene())
                exporter_log.export(temp_log)
                pdf.image(temp_log, x=10, w=190)
                os.remove(temp_log)

            pdf.output(fn)
            self.log_msg(f"PDF ataskaita issaugota: {fn}")
        except Exception as e:
            self.log_msg(f"Klaida PDF: {e}")