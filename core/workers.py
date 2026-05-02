import time
import math
import csv
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

class BodeSweepWorker(QThread):
    data_point = pyqtSignal(float, float)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager, dev_idx, start_f, stop_f, points, amp, gen_ch, osc_ch):
        super().__init__()
        self.mgr = manager
        self.dev_idx = dev_idx
        self.start_f = start_f
        self.stop_f = stop_f
        self.points = points
        self.amp = amp
        self.gen_ch = gen_ch
        self.osc_ch = osc_ch
        self.is_running = True

    def run(self):
        try:
            with self.mgr.lock:
                if not self.mgr.gen: raise Exception("Generatorius neprijungtas.")
                self.mgr.gen.set_output(True, self.gen_ch)

            freqs = np.logspace(math.log10(self.start_f), math.log10(self.stop_f), self.points)
            
            for i, f in enumerate(freqs):
                if not self.is_running: break
                
                with self.mgr.lock:
                    self.mgr.gen.apply_waveform("SINE", "FRQ", f, "AMP", self.amp, 0, 0, 50, 50, 0, 0, 0, self.gen_ch)
                
                # Suskaidytas laukimas reagavimui į stabdymo mygtuką
                wait_time = 0.5
                elapsed = 0
                while elapsed < wait_time and self.is_running:
                    time.sleep(0.05)
                    elapsed += 0.05
                    
                if not self.is_running: break
                
                val = None
                with self.mgr.lock:
                    if self.dev_idx == 0 and self.mgr.osc:
                        val = self.mgr.osc.get_measure("VPP", channel=self.osc_ch)
                    elif self.dev_idx == 1 and self.mgr.tti:
                        res = self.mgr.tti.get_reading()
                        if res: val = res[0]
                    elif self.dev_idx == 2 and self.mgr.esc:
                        val = self.mgr.esc.read_value()

                if val is not None:
                    self.data_point.emit(float(f), float(val))
                self.progress.emit(int((i + 1) / self.points * 100))

            with self.mgr.lock:
                if self.mgr.gen: self.mgr.gen.set_output(False, self.gen_ch)
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

class DataLoggerWorker(QThread):
    data_point = pyqtSignal(float, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager, dev_idx, mode_idx, interval_ms, duration_mins, filepath):
        super().__init__()
        self.mgr = manager
        self.dev_idx = dev_idx
        self.mode_idx = mode_idx
        self.interval_secs = interval_ms / 1000.0
        self.duration_secs = duration_mins * 60
        self.filepath = filepath
        self.is_running = True

    def run(self):
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
                    with self.mgr.lock:
                        if self.dev_idx == 0 and self.mgr.tti: 
                            res = self.mgr.tti.get_reading()
                            val = res[0] if (res and res[0] is not None) else 0.0
                        elif self.dev_idx == 1 and self.mgr.esc:
                            val = self.mgr.esc.read_value() or 0.0

                    writer.writerow([f"{t_elapsed:.2f}", f"{val:.6e}"])
                    f.flush()
                    self.data_point.emit(float(t_elapsed), float(val))
                    
                    # Suskaidytas intervalas reagavimui į stabdymo mygtuką
                    wait_start = time.time()
                    while (time.time() - wait_start) < self.interval_secs and self.is_running:
                        time.sleep(0.05)
                        
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))