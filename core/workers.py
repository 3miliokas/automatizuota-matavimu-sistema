import time
import math
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class BodeSweepWorker(QThread):
    data_point = pyqtSignal(float, float)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, gen_addr, dev_idx, meas_addr, start_f, stop_f, points, amp, gen_ch, osc_ch):
        super().__init__()
        self.gen_addr = gen_addr
        self.dev_idx = dev_idx
        self.meas_addr = meas_addr
        self.start_f = start_f
        self.stop_f = stop_f
        self.points = points
        self.amp = amp
        self.gen_ch = gen_ch
        self.osc_ch = osc_ch
        self.is_running = True

    def run(self):
        try:
            gen = SiglentSDG(self.gen_addr)
            gen.set_output(True, self.gen_ch)

            freqs = np.logspace(math.log10(self.start_f), math.log10(self.stop_f), self.points)

            for i, freq in enumerate(freqs):
                if not self.is_running: break
                
                gen.apply_waveform("Sine", freq, self.amp, 0, 0, 50, 50, channel=self.gen_ch)
                time.sleep(0.6) 

                val = 0.0
                if self.dev_idx == 0: 
                    osc = RigolMSO(self.meas_addr)
                    meas = osc.get_measure("VPP", channel=self.osc_ch)
                    osc.close()
                    val = meas if meas is not None and meas < 1e15 else 0.0

                elif self.dev_idx == 1: 
                    tti = TTi1604(self.meas_addr)
                    tti.send_command("AC")
                    res = tti.get_reading()
                    tti.close()
                    val = res[0] if (res and res[0] is not None) else 0.0

                elif self.dev_idx == 2: 
                    esc = Escort3136A(self.meas_addr)
                    # Jei prietaisas nepalaiko AC komandos per API, matuojama DC
                    meas = esc.get_voltage_dc() 
                    esc.close()
                    val = meas if meas is not None else 0.0
                
                self.data_point.emit(float(freq), float(val))
                self.progress.emit(int((i + 1) / self.points * 100))

            gen.set_output(False, self.gen_ch)
            gen.close()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class DataLoggerWorker(QThread):
    data_point = pyqtSignal(float, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, dev_idx, addr, mode_idx, interval, duration_mins, filepath):
        super().__init__()
        self.dev_idx = dev_idx
        self.addr = addr
        self.mode_idx = mode_idx
        self.interval = interval
        self.duration_secs = duration_mins * 60
        self.filepath = filepath
        self.is_running = True

    def run(self):
        import csv
        try:
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time_s", "Value"])
                start_time = time.time()
                
                while self.is_running:
                    t_elapsed = time.time() - start_time
                    if self.duration_secs > 0 and t_elapsed > self.duration_secs:
                        break

                    val = 0.0
                    if self.dev_idx == 0: 
                        tti = TTi1604(self.addr)
                        res = tti.get_reading()
                        tti.close()
                        val = res[0] if (res and res[0] is not None) else 0.0
                    else: 
                        esc = Escort3136A(self.addr)
                        meas = esc.get_voltage_dc() if self.mode_idx == 0 else esc.get_current_dc()
                        esc.close()
                        val = meas if meas is not None else 0.0

                    writer.writerow([f"{t_elapsed:.2f}", f"{val:.6e}"])
                    f.flush()
                    self.data_point.emit(float(t_elapsed), float(val))
                    
                    time.sleep(self.interval)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))