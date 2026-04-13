import os
import csv
import math
from datetime import datetime
import numpy as np

import pyvisa
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer

# Importuojame atskirtą UI klasę
from gui.ui_layout import Ui_MainWindow
# Importuojame atskirtus fono darbininkus
from core.workers import BodeSweepWorker, DataLoggerWorker

# Aparatūros moduliai
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class MainWindow(QMainWindow):
    """Pagrindinė programos klasė (Controller). Sujungia GUI signalus su aparatūros komandomis."""
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)

        # Grafikos būsenos kintamieji
        self.x_data, self.y_data = [], []
        self.data_line = self.ui.graph_widget.plot(self.x_data, self.y_data, pen='y')
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_from_rigol)

        # Bode kintamieji
        self.bode_worker = None
        self.bode_freqs = [] 
        self.bode_x = []     
        self.bode_y = []     
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')

        # Logikos kintamieji
        self.log_worker = None
        self.log_x = []; self.log_y = []
        self.log_line = self.ui.log_graph.plot(self.log_x, self.log_y, pen='g')

        # FFT kintamieji
        self.fft_x = []; self.fft_y = []
        self.fft_line = self.ui.fft_graph.plot(self.fft_x, self.fft_y, pen='m', fillLevel=0, brush=(156,39,176,50))

        self.connect_signals()

    def connect_signals(self):
        """Sujungia vartotojo sąsajos mygtukus su klasės funkcijomis."""
        self.ui.btn_scan.clicked.connect(self.scan_devices)
        self.ui.btn_apply_gen.clicked.connect(self.apply_generator)
        self.ui.btn_auto.clicked.connect(self.trigger_autoscale)
        self.ui.btn_run.clicked.connect(lambda: self.control_osc("run"))
        self.ui.btn_stop_osc.clicked.connect(lambda: self.control_osc("stop"))
        self.ui.btn_meas_all.clicked.connect(self.fetch_all_measurements)
        self.ui.btn_screenshot.clicked.connect(self.save_rigol_screenshot)
        self.ui.btn_start_stream.clicked.connect(self.start_stream)
        self.ui.btn_stop_stream.clicked.connect(self.stop_stream)
        self.ui.btn_export.clicked.connect(self.export_csv)
        self.ui.btn_tti_v.clicked.connect(lambda: self.fetch_tti("V"))
        self.ui.btn_tti_a.clicked.connect(lambda: self.fetch_tti("A"))
        self.ui.btn_escort_v.clicked.connect(lambda: self.fetch_escort("V"))
        self.ui.btn_escort_a.clicked.connect(lambda: self.fetch_escort("A"))
        self.ui.btn_start_bode.clicked.connect(self.start_bode_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_bode_sweep)
        self.ui.btn_export_bode.clicked.connect(self.export_bode_csv)
        self.ui.btn_start_log.clicked.connect(self.start_logging)
        self.ui.btn_stop_log.clicked.connect(self.stop_logging)
        self.ui.btn_calc_fft.clicked.connect(self.calculate_fft)
        self.ui.btn_generate_pdf.clicked.connect(self.generate_pdf_report)

    def log_msg(self, text):
        """Spausdina pranešimus į vartotojo sąsajos žurnalą apačioje."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.log_console.append(f"[{timestamp}] {text}")
        self.ui.log_console.verticalScrollBar().setValue(self.ui.log_console.verticalScrollBar().maximum())

    def format_eng(self, val, unit="V"):
        """Formatuoja skaičius inžineriniu formatu (mV, µV, kHz ir t.t.)."""
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

    def scan_devices(self):
        """Naudoja PyVISA ir PySerial ieškant prijungtų prietaisų."""
        self.ui.combo_gen.clear(); self.ui.combo_osc.clear(); self.ui.combo_tti.clear(); self.ui.combo_escort.clear()
        self.log_msg("Skenuojama VISA ir COM prievadai...")
        rm = pyvisa.ResourceManager()
        for addr in rm.list_resources():
            try:
                inst = rm.open_resource(addr)
                inst.timeout = 500
                idn = inst.query("*IDN?").strip()
                inst.close()
                name = idn.split(',')[1] if len(idn.split(',')) > 1 else idn
                if "SDG" in idn: self.ui.combo_gen.addItem(f"{name} [{addr}]", addr)
                elif "DS1" in idn or "MSO" in idn: self.ui.combo_osc.addItem(f"{name} [{addr}]", addr)
            except Exception: pass
        for port in serial.tools.list_ports.comports():
            port_info = f"{port.device} - {port.description}"
            self.ui.combo_tti.addItem(port_info, port.device)
            self.ui.combo_escort.addItem(port_info, port.device)
        self.log_msg("Skenavimas baigtas.")

    # --- BAZINIAI MATAVIMAI IR VALDYMAS ---
    def get_freq_hz(self):
        m = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
        return self.ui.freq_in.value() * m[self.ui.freq_unit.currentText()]

    def apply_generator(self):
        addr = self.ui.combo_gen.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas generatorius.")
        try:
            gen = SiglentSDG(addr)
            gen.apply_waveform(self.ui.wave_type.currentText(), self.get_freq_hz(), 
                               self.ui.amp_in.value(), self.ui.offset_in.value(),
                               self.ui.phase_in.value(), self.ui.duty_in.value(), self.ui.sym_in.value())
            gen.close()
            self.log_msg("Generatoriaus parametrai atnaujinti.")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def trigger_autoscale(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.auto_scale(); osc.close()
            self.log_msg("Iškviestas oscilografo Auto-Scale.")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def control_osc(self, state):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.run() if state == "run" else osc.stop()
            osc.close()
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def fetch_all_measurements(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        was_streaming = self.timer.isActive()
        if was_streaming: self.timer.stop()
        try:
            osc = RigolMSO(addr)
            self.ui.lbl_meas_vpp.setText(f"Vpp: {self.format_eng(osc.get_measure('VPP'), 'V')}")
            self.ui.lbl_meas_vmax.setText(f"Vmax: {self.format_eng(osc.get_measure('VMAX'), 'V')}")
            self.ui.lbl_meas_vmin.setText(f"Vmin: {self.format_eng(osc.get_measure('VMIN'), 'V')}")
            self.ui.lbl_meas_freq.setText(f"Dažnis: {self.format_eng(osc.get_measure('FREQ'), 'Hz')}")
            self.ui.lbl_meas_rise.setText(f"Rise Time: {self.format_eng(osc.get_measure('RISetime'), 's')}")
            self.ui.lbl_meas_fall.setText(f"Fall Time: {self.format_eng(osc.get_measure('FALLtime'), 's')}")
            osc.close()
            self.log_msg("Aparatūriniai matavimai atnaujinti.")
        except Exception as e: self.log_msg(f"Klaida: {e}")
        if was_streaming: self.timer.start(500)

    def start_stream(self):
        if not self.ui.combo_osc.currentData(): return self.log_msg("Nepasirinktas oscilografas.")
        self.timer.start(500) 
        self.log_msg("Pradėtas gyvas oscilogramos atvaizdavimas.")

    def stop_stream(self):
        self.timer.stop()
        self.log_msg("Oscilograma sustabdyta.")

    def update_plot_from_rigol(self):
        addr = self.ui.combo_osc.currentData()
        try:
            osc = RigolMSO(addr)
            t, v = osc.get_waveform_data(channel=1)
            osc.close()
            self.x_data, self.y_data = t, v
            self.data_line.setData(self.x_data, self.y_data)
        except pyvisa.errors.VisaIOError: pass 
        except Exception: pass

    def export_csv(self):
        if not self.x_data: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Oscilogramą", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Time", "Voltage"])
                for x, y in zip(self.x_data, self.y_data): w.writerow([f"{x:.10e}", f"{y:.10e}"])
            self.log_msg("CSV eksportuotas sėkmingai.")

    def save_rigol_screenshot(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        was_streaming = self.timer.isActive()
        if was_streaming: self.timer.stop()
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti ekrano nuotrauką", "rigol_screen.png", "PNG (*.png)")
        if fn:
            try:
                osc = RigolMSO(addr)
                img_data = osc.get_screenshot()
                osc.close()
                with open(fn, "wb") as f: f.write(img_data)
                self.log_msg("Nuotrauka išsaugota.")
            except Exception as e: self.log_msg(f"Klaida: {e}")
        if was_streaming: self.timer.start(500)

    def fetch_tti(self, mode):
        port = self.ui.combo_tti.currentData()
        if not port: return
        try:
            tti = TTi1604(port)
            val = tti.get_voltage() if mode == "V" else tti.get_current()
            unit = "V" if mode == "V" else "A"
            tti.close()
            if val is not None: self.ui.lbl_tti_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
        except Exception as e: self.log_msg(f"Klaida TTi: {e}")

    def fetch_escort(self, mode):
        port = self.ui.combo_escort.currentData()
        if not port: return
        try:
            escort = Escort3136A(port)
            val = escort.get_voltage_dc() if mode == "V" else escort.get_current_dc()
            unit = "V" if mode == "V" else "A"
            escort.close()
            if val is not None: self.ui.lbl_escort_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
        except Exception as e: self.log_msg(f"Klaida Escort: {e}")

    # --- KOMPLEKSINIAI MODULIAI ---
    def calculate_fft(self):
        """Atlieka skaitmeninę spektrinę analizę naudodamas numpy."""
        addr = self.ui.combo_osc.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas oscilografas FFT.")
        was_streaming = self.timer.isActive()
        if was_streaming: self.timer.stop()
        self.log_msg("Nuskaitomi duomenys FFT skaičiavimui...")
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
            self.fft_y[0] = 0 # Ignoruojame DC komponentę
            self.fft_line.setData(self.fft_x, self.fft_y)
            
            peak_idx = np.argmax(self.fft_y)
            peak_freq = self.fft_x[peak_idx]
            peak_amp = self.fft_y[peak_idx]
            self.ui.lbl_fft_peak.setText(f"Pagrindinė harmonika (Pikas): {self.format_eng(peak_freq, 'Hz')} ({peak_amp:.3f} V)")
            self.log_msg(f"FFT atliktas. Pikas: {peak_freq:.2f} Hz")
        except Exception as e:
            self.log_msg(f"FFT Klaida: {e}")
        if was_streaming: self.timer.start(500)

    def start_logging(self):
        """Inicijuoja Data Logger procesą fone."""
        dev_idx = self.ui.log_device.currentIndex()
        addr = self.ui.combo_tti.currentData() if dev_idx == 0 else self.ui.combo_escort.currentData()
        if not addr: return self.log_msg("Klaida: Nepasirinktas prietaisas.")
        
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti žurnalą", "log.csv", "CSV (*.csv)")
        if not fn: return
        
        self.log_x.clear(); self.log_y.clear(); self.log_line.setData(self.log_x, self.log_y)
        self.ui.btn_start_log.setEnabled(False)
        self.log_worker = DataLoggerWorker(dev_idx, addr, self.ui.log_mode.currentIndex(), self.ui.log_interval.value(), self.ui.log_duration.value(), fn)
        self.log_worker.data_point.connect(self.on_log_data)
        self.log_worker.finished.connect(self.on_log_finished)
        self.log_worker.error.connect(lambda e: self.log_msg(f"Klaida: {e}"))
        self.log_worker.start()
        self.log_msg("Duomenų registravimas pradėtas.")

    def on_log_data(self, t, val):
        self.log_x.append(t); self.log_y.append(val); self.log_line.setData(self.log_x, self.log_y)
        unit = "V" if self.ui.log_mode.currentIndex() == 0 else "A"
        self.ui.lbl_log_current.setText(f"Reikšmė: {self.format_eng(val, unit)}")

    def stop_logging(self):
        if self.log_worker and self.log_worker.isRunning(): 
            self.log_worker.is_running = False

    def on_log_finished(self):
        self.ui.btn_start_log.setEnabled(True)
        self.log_msg("Registravimas sustabdytas.")

    def start_bode_sweep(self):
        """Inicijuoja Bode Plot matavimo procesą fone."""
        gen_addr = self.ui.combo_gen.currentData()
        if not gen_addr: return self.log_msg("Klaida: Nepasirinktas generatorius.")
        dev_idx = self.ui.bode_device.currentIndex()
        meas_addr = None
        if dev_idx == 0: meas_addr = self.ui.combo_osc.currentData()
        elif dev_idx == 1: meas_addr = self.ui.combo_tti.currentData()
        elif dev_idx == 2: meas_addr = self.ui.combo_escort.currentData()
        if not meas_addr: return self.log_msg("Klaida matavimo prietaise!")
        
        if self.timer.isActive(): self.timer.stop()
        self.bode_freqs.clear(); self.bode_x.clear(); self.bode_y.clear(); self.bode_line.setData(self.bode_x, self.bode_y)
        self.ui.bode_progress.setValue(0); self.ui.btn_start_bode.setEnabled(False)
        
        self.bode_worker = BodeSweepWorker(gen_addr, dev_idx, meas_addr, self.ui.bode_start_f.value(), self.ui.bode_stop_f.value(), self.ui.bode_points.value(), self.ui.bode_amp.value())
        self.bode_worker.data_point.connect(self.on_bode_data)
        self.bode_worker.progress.connect(self.ui.bode_progress.setValue)
        self.bode_worker.finished.connect(self.on_bode_finished)
        self.bode_worker.error.connect(lambda e: self.log_msg(f"Klaida: {e}"))
        self.bode_worker.start()
        self.log_msg("Bode Plot matavimas pradedamas...")

    def on_bode_data(self, freq, val):
        v_in = self.ui.bode_amp.value()
        if val <= 0: val = 1e-6
        db = 20 * math.log10(val / v_in)
        self.bode_freqs.append(freq); self.bode_x.append(math.log10(freq)); self.bode_y.append(db)
        self.bode_line.setData(self.bode_x, self.bode_y)

    def stop_bode_sweep(self):
        if self.bode_worker and self.bode_worker.isRunning(): 
            self.bode_worker.is_running = False

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

    def generate_pdf_report(self):
        """Sugeneruoja profesionalų PDF dokumentą su įrangos nustatymais ir grafikais."""
        try:
            from fpdf import FPDF
            import pyqtgraph.exporters
        except ImportError:
            return self.log_msg("Truksta 'fpdf' bibliotekos.")

        fn, _ = QFileDialog.getSaveFileName(self, "Issaugoti PDF", "matavimu_protokolas.pdf", "PDF (*.pdf)")
        if not fn: return

        self.log_msg("Generuojamas PDF protokolas...")
        try:
            pdf = FPDF()
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Automatizuotu Matavimu Protokolas", ln=True, align='C')
            
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Data ir laikas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
            serial_text = self.ui.input_serial.text() if self.ui.input_serial.text() else "Nenurodyta"
            pdf.cell(200, 10, txt=f"Bandomo prietaiso Serijos Nr.: {serial_text}", ln=True)
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="1. Generatoriaus Nustatymai (SDG):", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 8, txt=f"Tipas: {self.ui.wave_type.currentText()}", ln=True)
            pdf.cell(200, 8, txt=f"Daznis: {self.ui.freq_in.value()} {self.ui.freq_unit.currentText()}", ln=True)
            pdf.cell(200, 8, txt=f"Amplitude: {self.ui.amp_in.value()} Vpp", ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="2. Aparaturiniai Matavimai (MSO):", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 8, txt=self.ui.lbl_meas_vpp.text(), ln=True)
            pdf.cell(200, 8, txt=self.ui.lbl_meas_freq.text().replace("ž", "z").replace("Dažnis", "Daznis"), ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="3. Oscilograma:", ln=True)
            
            # Grafiko eksportas i vaizda
            temp_img = "temp_plot.png"
            exporter = pyqtgraph.exporters.ImageExporter(self.ui.graph_widget.scene())
            exporter.export(temp_img)
            
            pdf.image(temp_img, x=10, w=190)
            pdf.output(fn)
            self.log_msg(f"PDF ataskaita sekmingai isaugota: {fn}")
            
            if os.path.exists(temp_img):
                os.remove(temp_img)
                
        except Exception as e:
            self.log_msg(f"Klaida generuojant PDF: {e}")