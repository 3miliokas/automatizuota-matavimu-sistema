import csv
import math
import time
from datetime import datetime
import numpy as np
import pyvisa
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

from gui.ui_layout import Ui_MainWindow
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

# =======================================================
# FONO PROCESAS: Bode Plot automatizacija (Multithreading)
# =======================================================
class BodeSweepWorker(QThread):
    progress = pyqtSignal(int)
    data_point = pyqtSignal(float, float) # Dažnis, Įtampa
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, gen_addr, meas_dev, meas_addr, start_f, stop_f, points, amp):
        super().__init__()
        self.gen_addr = gen_addr
        self.meas_dev = meas_dev # 0=Rigol, 1=TTi, 2=Escort
        self.meas_addr = meas_addr
        self.start_f = start_f
        self.stop_f = stop_f
        self.points = points
        self.amp = amp
        self.is_running = True

    def run(self):
        try:
            # Sugeneruojame logaritminį dažnių vektorių (pvz. nuo 10 Hz iki 10 kHz)
            freqs = np.logspace(np.log10(self.start_f), np.log10(self.stop_f), self.points)
            
            # Prisijungiame prie instrumentų
            gen = SiglentSDG(self.gen_addr)
            meas = None
            if self.meas_dev == 0: meas = RigolMSO(self.meas_addr)
            elif self.meas_dev == 1: meas = TTi1604(self.meas_addr)
            elif self.meas_dev == 2: meas = Escort3136A(self.meas_addr)

            for i, f in enumerate(freqs):
                if not self.is_running:
                    break
                
                # Nustatome dažnį
                gen.apply_waveform("Sine", f, self.amp, 0, 0, 50, 50)
                time.sleep(0.5) # Nusistovėjimo laikas grandinei (500ms)

                # Nuskaitome atsaką
                val = 0.0
                if self.meas_dev == 0:
                    val = meas.get_measure("VPP")
                elif self.meas_dev == 1:
                    val = meas.get_voltage()
                elif self.meas_dev == 2:
                    val = meas.get_voltage_dc()
                
                if val is None or val > 1e15: 
                    val = 1e-6 # Filtruojame šiukšles, kad dB apskaičiavimas nenulūžtų

                self.data_point.emit(f, val)
                self.progress.emit(int((i + 1) / self.points * 100))

            gen.close()
            if meas: meas.close()
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

# =======================================================
# PAGRINDINĖ PROGRAMOS KLASĖ
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)

        # Oscilogramos kintamieji
        self.x_data, self.y_data = [], []
        self.data_line = self.ui.graph_widget.plot(self.x_data, self.y_data, pen='y')
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_from_rigol)

        # Bode Plot kintamieji
        self.bode_worker = None
        self.bode_freqs = [] # Originalūs dažniai eksportui
        self.bode_x = []     # Logaritminiai dažniai braižymui (PyQtGraph formatas)
        self.bode_y = []     # Decibelai
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')

        # Signalų susiejimas
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
        
        # Bode signalai
        self.ui.btn_start_bode.clicked.connect(self.start_bode_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_bode_sweep)
        self.ui.btn_export_bode.clicked.connect(self.export_bode_csv)

    # --- BODE PLOT FUNKCIJOS ---

    def start_bode_sweep(self):
        gen_addr = self.ui.combo_gen.currentData()
        if not gen_addr:
            return self.log_msg("Klaida: Nepasirinktas generatorius.")
            
        dev_idx = self.ui.bode_device.currentIndex()
        meas_addr = None
        if dev_idx == 0: meas_addr = self.ui.combo_osc.currentData()
        elif dev_idx == 1: meas_addr = self.ui.combo_tti.currentData()
        elif dev_idx == 2: meas_addr = self.ui.combo_escort.currentData()
        
        if not meas_addr:
            return self.log_msg("Klaida: Nepasirinktas matavimo prietaisas!")

        # Sustabdome gyvą oscilogramą, kad prietaisas nepersikrautų nuo komandų
        if self.timer.isActive():
            self.timer.stop()

        self.bode_freqs.clear()
        self.bode_x.clear()
        self.bode_y.clear()
        self.bode_line.setData(self.bode_x, self.bode_y)
        self.ui.bode_progress.setValue(0)
        self.ui.btn_start_bode.setEnabled(False)
        self.log_msg("Bode Plot matavimas pradedamas...")

        self.bode_worker = BodeSweepWorker(
            gen_addr=gen_addr, meas_dev=dev_idx, meas_addr=meas_addr,
            start_f=self.ui.bode_start_f.value(), stop_f=self.ui.bode_stop_f.value(),
            points=self.ui.bode_points.value(), amp=self.ui.bode_amp.value()
        )
        self.bode_worker.data_point.connect(self.on_bode_data)
        self.bode_worker.progress.connect(self.ui.bode_progress.setValue)
        self.bode_worker.finished.connect(self.on_bode_finished)
        self.bode_worker.error.connect(lambda e: self.log_msg(f"Bode klaida: {e}"))
        self.bode_worker.start()

    def on_bode_data(self, freq, val):
        v_in = self.ui.bode_amp.value()
        if val <= 0: val = 1e-6
        
        # Apskaičiuojame stiprinimą decibelais (dB = 20 * log10(Vout/Vin))
        db = 20 * math.log10(val / v_in)
        
        self.bode_freqs.append(freq)
        self.bode_x.append(math.log10(freq)) # Grafikas su setLogMode() reikalauja log10() duomenų
        self.bode_y.append(db)
        self.bode_line.setData(self.bode_x, self.bode_y)
        self.log_msg(f"F: {freq:.1f} Hz, Vout: {val:.4f} V, Stiprinimas: {db:.2f} dB")

    def stop_bode_sweep(self):
        if self.bode_worker and self.bode_worker.isRunning():
            self.bode_worker.is_running = False
            self.log_msg("Stabdoma...")

    def on_bode_finished(self):
        self.log_msg("Bode Plot matavimas baigtas.")
        self.ui.btn_start_bode.setEnabled(True)

    def export_bode_csv(self):
        if not self.bode_freqs: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Bode duomenis", "bode_plot.csv", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Frequency_Hz", "Gain_dB"])
                for f_hz, db in zip(self.bode_freqs, self.bode_y):
                    w.writerow([f"{f_hz:.2f}", f"{db:.4f}"])
            self.log_msg("Bode duomenys eksportuoti sėkmingai.")

    # --- BAZINĖS FUNKCIJOS (Nepakeistos) ---

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

    def scan_devices(self):
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

    def get_freq_hz(self):
        m = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
        return self.ui.freq_in.value() * m[self.ui.freq_unit.currentText()]

    def apply_generator(self):
        addr = self.ui.combo_gen.currentData()
        if not addr: return self.log_msg("Nepasirinktas generatorius.")
        try:
            gen = SiglentSDG(addr)
            gen.apply_waveform(self.ui.wave_type.currentText(), self.get_freq_hz(), 
                               self.ui.amp_in.value(), self.ui.offset_in.value(),
                               self.ui.phase_in.value(), self.ui.duty_in.value(), self.ui.sym_in.value())
            gen.close()
            self.log_msg("Generatorius atnaujintas.")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def trigger_autoscale(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.auto_scale()
            osc.close()
            self.log_msg("Rigol Auto-Scale iškviestas.")
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

        self.log_msg("Skaitomi aparatūriniai matavimai...")
        try:
            osc = RigolMSO(addr)
            self.ui.lbl_meas_vpp.setText(f"Vpp: {self.format_eng(osc.get_measure('VPP'), 'V')}")
            self.ui.lbl_meas_vmax.setText(f"Vmax: {self.format_eng(osc.get_measure('VMAX'), 'V')}")
            self.ui.lbl_meas_vmin.setText(f"Vmin: {self.format_eng(osc.get_measure('VMIN'), 'V')}")
            self.ui.lbl_meas_freq.setText(f"Dažnis: {self.format_eng(osc.get_measure('FREQ'), 'Hz')}")
            self.ui.lbl_meas_rise.setText(f"Rise Time: {self.format_eng(osc.get_measure('RISetime'), 's')}")
            self.ui.lbl_meas_fall.setText(f"Fall Time: {self.format_eng(osc.get_measure('FALLtime'), 's')}")
            osc.close()
        except Exception as e: self.log_msg(f"Klaida: {e}")

        if was_streaming: self.timer.start(500)

    def start_stream(self):
        if not self.ui.combo_osc.currentData(): return self.log_msg("Klaida: Nepasirinktas oscilografas.")
        self.timer.start(500) 
        self.log_msg("Duomenų srautas pradėtas.")

    def stop_stream(self):
        self.timer.stop()
        self.log_msg("Duomenų srautas sustabdytas.")

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
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Time", "Voltage"])
                for x, y in zip(self.x_data, self.y_data):
                    w.writerow([f"{x:.10e}", f"{y:.10e}"])
            self.log_msg("Eksportuota sėkmingai.")

    def save_rigol_screenshot(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return self.log_msg("Klaida.")
        was_streaming = self.timer.isActive()
        if was_streaming: self.timer.stop()

        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti ekrano nuotrauką", "rigol_screen.png", "PNG (*.png)")
        if fn:
            try:
                osc = RigolMSO(addr)
                img_data = osc.get_screenshot()
                osc.close()
                with open(fn, "wb") as f: f.write(img_data)
                self.log_msg(f"Nuotrauka sėkmingai išsaugota: {fn}")
            except Exception as e: self.log_msg(f"Klaida: {e}")

        if was_streaming: self.timer.start(500)

    def fetch_tti(self, mode):
        port = self.ui.combo_tti.currentData()
        if not port: return self.log_msg("Klaida.")
        try:
            tti = TTi1604(port)
            val = tti.get_voltage() if mode == "V" else tti.get_current()
            unit = "V" if mode == "V" else "A"
            tti.close()
            if val is not None: self.ui.lbl_tti_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
            else: self.ui.lbl_tti_res.setText("Reikšmė: Klaida")
        except Exception as e: self.log_msg(f"Klaida: {e}")

    def fetch_escort(self, mode):
        port = self.ui.combo_escort.currentData()
        if not port: return self.log_msg("Klaida.")
        try:
            escort = Escort3136A(port)
            val = escort.get_voltage_dc() if mode == "V" else escort.get_current_dc()
            unit = "V" if mode == "V" else "A"
            escort.close()
            if val is not None: self.ui.lbl_escort_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
            else: self.ui.lbl_escort_res.setText("Reikšmė: Klaida")
        except Exception as e: self.log_msg(f"Klaida: {e}")