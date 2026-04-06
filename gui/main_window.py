import csv
import math
import time
from datetime import datetime
import numpy as np
import pyvisa
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

from gui.ui_layout import Ui_MainWindow
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

# =======================================================
# FONO PROCESAS 1: Bode Plot automatizacija
# =======================================================
class BodeSweepWorker(QThread):
    progress = pyqtSignal(int)
    data_point = pyqtSignal(float, float) 
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, gen_addr, meas_dev, meas_addr, start_f, stop_f, points, amp):
        super().__init__()
        self.gen_addr = gen_addr
        self.meas_dev = meas_dev 
        self.meas_addr = meas_addr
        self.start_f = start_f
        self.stop_f = stop_f
        self.points = points
        self.amp = amp
        self.is_running = True

    def run(self):
        try:
            freqs = np.logspace(np.log10(self.start_f), np.log10(self.stop_f), self.points)
            gen = SiglentSDG(self.gen_addr)
            meas = None
            if self.meas_dev == 0: meas = RigolMSO(self.meas_addr)
            elif self.meas_dev == 1: meas = TTi1604(self.meas_addr)
            elif self.meas_dev == 2: meas = Escort3136A(self.meas_addr)

            for i, f in enumerate(freqs):
                if not self.is_running: break
                gen.apply_waveform("Sine", f, self.amp, 0, 0, 50, 50)
                time.sleep(0.5) 

                val = 0.0
                if self.meas_dev == 0: val = meas.get_measure("VPP")
                elif self.meas_dev == 1: val = meas.get_voltage()
                elif self.meas_dev == 2: val = meas.get_voltage_dc()
                
                if val is None or val > 1e15: val = 1e-6 
                self.data_point.emit(f, val)
                self.progress.emit(int((i + 1) / self.points * 100))

            gen.close()
            if meas: meas.close()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# =======================================================
# FONO PROCESAS 2: Ilgalaikis registravimas (Data Logging)
# =======================================================
class DataLoggerWorker(QThread):
    data_point = pyqtSignal(float, float) # T_elapsed, Value
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, dev_idx, addr, mode_idx, interval, duration_m, filepath):
        super().__init__()
        self.dev_idx = dev_idx # 0=TTi, 1=Escort
        self.addr = addr
        self.mode_idx = mode_idx # 0=V, 1=A
        self.interval = interval
        self.duration_s = duration_m * 60
        self.filepath = filepath
        self.is_running = True

    def run(self):
        try:
            meas = None
            if self.dev_idx == 0: meas = TTi1604(self.addr)
            elif self.dev_idx == 1: meas = Escort3136A(self.addr)

            with open(self.filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Time_s", "Value"])
                
                start_time = time.time()
                while self.is_running:
                    loop_start = time.time()
                    elapsed = loop_start - start_time
                    
                    if self.duration_s > 0 and elapsed >= self.duration_s:
                        break

                    val = None
                    if self.dev_idx == 0:
                        val = meas.get_voltage() if self.mode_idx == 0 else meas.get_current()
                    elif self.dev_idx == 1:
                        val = meas.get_voltage_dc() if self.mode_idx == 0 else meas.get_current_dc()

                    if val is not None:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        writer.writerow([ts, f"{elapsed:.2f}", f"{val:.6e}"])
                        f.flush() # Užtikrina tiesioginį disko įrašymą
                        self.data_point.emit(elapsed, val)

                    # Palaiko tikslų intervalą neatsižvelgiant į išskaitymo vėlavimą
                    process_time = time.time() - loop_start
                    sleep_time = self.interval - process_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

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

        # Bode kintamieji
        self.bode_worker = None
        self.bode_freqs = [] 
        self.bode_x = []     
        self.bode_y = []     
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')

        # Data Logger kintamieji
        self.log_worker = None
        self.log_x = []
        self.log_y = []
        self.log_line = self.ui.log_graph.plot(self.log_x, self.log_y, pen='g')

        # Signalai
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

    # --- DATA LOGGER FUNKCIJOS ---
    def start_logging(self):
        dev_idx = self.ui.log_device.currentIndex()
        addr = self.ui.combo_tti.currentData() if dev_idx == 0 else self.ui.combo_escort.currentData()
        
        if not addr:
            return self.log_msg("Klaida: Nepasirinktas prietaisas registravimui.")

        fn, _ = QFileDialog.getSaveFileName(self, "Pasirinkite failą įrašymui", "matavimai_log.csv", "CSV (*.csv)")
        if not fn: return

        self.log_x.clear()
        self.log_y.clear()
        self.log_line.setData(self.log_x, self.log_y)
        self.ui.btn_start_log.setEnabled(False)
        self.log_msg(f"Pradedamas duomenų registravimas į: {fn}")

        self.log_worker = DataLoggerWorker(
            dev_idx=dev_idx, addr=addr, mode_idx=self.ui.log_mode.currentIndex(),
            interval=self.ui.log_interval.value(), duration_m=self.ui.log_duration.value(),
            filepath=fn
        )
        self.log_worker.data_point.connect(self.on_log_data)
        self.log_worker.finished.connect(self.on_log_finished)
        self.log_worker.error.connect(lambda e: self.log_msg(f"Logger klaida: {e}"))
        self.log_worker.start()

    def on_log_data(self, t, val):
        self.log_x.append(t)
        self.log_y.append(val)
        self.log_line.setData(self.log_x, self.log_y)
        unit = "V" if self.ui.log_mode.currentIndex() == 0 else "A"
        self.ui.lbl_log_current.setText(f"Dabartinė reikšmė: {self.format_eng(val, unit)}")

    def stop_logging(self):
        if self.log_worker and self.log_worker.isRunning():
            self.log_worker.is_running = False
            self.log_msg("Stabdomas registravimas...")

    def on_log_finished(self):
        self.log_msg("Duomenų registravimas baigtas.")
        self.ui.btn_start_log.setEnabled(True)

    # --- BODE PLOT FUNKCIJOS ---
    def start_bode_sweep(self):
        gen_addr = self.ui.combo_gen.currentData()
        if not gen_addr: return self.log_msg("Klaida: Nepasirinktas generatorius.")
        dev_idx = self.ui.bode_device.currentIndex()
        meas_addr = None
        if dev_idx == 0: meas_addr = self.ui.combo_osc.currentData()
        elif dev_idx == 1: meas_addr = self.ui.combo_tti.currentData()
        elif dev_idx == 2: meas_addr = self.ui.combo_escort.currentData()
        if not meas_addr: return self.log_msg("Klaida: Nepasirinktas matavimo prietaisas!")

        if self.timer.isActive(): self.timer.stop()

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
        db = 20 * math.log10(val / v_in)
        self.bode_freqs.append(freq)
        self.bode_x.append(math.log10(freq)) 
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
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Bode", "bode_plot.csv", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Frequency_Hz", "Gain_dB"])
                for f_hz, db in zip(self.bode_freqs, self.bode_y):
                    w.writerow([f"{f_hz:.2f}", f"{db:.4f}"])
            self.log_msg("Bode eksportuoti sėkmingai.")

    # --- BAZINĖS FUNKCIJOS ---
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