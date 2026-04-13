import time
import csv
import math
from datetime import datetime
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class BodeSweepWorker(QThread):
    """
    Fono procesas uždaro ciklo dažninei charakteristikai (Bode Plot) matuoti.
    Saugiai atskiria aparatūros valdymą nuo GUI gijos.
    """
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
                
                # Siunčiame dažnį į generatorių ir laukiame stabilizacijos
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

class DataLoggerWorker(QThread):
    """
    Fono procesas ilgalaikiam duomenų registravimui iš multimetrų.
    Duomenys rašomi tiesiai į disko failą saugumui užtikrinti.
    """
    data_point = pyqtSignal(float, float) 
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, dev_idx, addr, mode_idx, interval, duration_m, filepath):
        super().__init__()
        self.dev_idx = dev_idx 
        self.addr = addr
        self.mode_idx = mode_idx 
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
                        f.flush() # Tiesiausias kelias į HDD/SSD
                        self.data_point.emit(elapsed, val)

                    # Intervalo kompensavimas
                    process_time = time.time() - loop_start
                    sleep_time = self.interval - process_time
                    if sleep_time > 0: 
                        time.sleep(sleep_time)

            if meas: meas.close()
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))