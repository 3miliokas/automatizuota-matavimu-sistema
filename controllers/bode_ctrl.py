import math
from core.workers import BodeSweepWorker

class BodeController:
    def __init__(self, main, ui, mgr):
        self.main = main; self.ui = ui; self.mgr = mgr
        self.worker = None
        self.ui.btn_start_bode.clicked.connect(self.start_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_sweep)

    def start_sweep(self):
        self.ui.graph_tabs.setCurrentIndex(1)
        if hasattr(self.main.osc_ctrl, 'stream_timer') and self.main.osc_ctrl.stream_timer.isActive():
            self.ui.btn_stream.setChecked(False)
        
        self.main.bode_freqs.clear(); self.main.bode_x.clear(); self.main.bode_y.clear(); self.main.bode_line.setData([], [])
        self.ui.btn_start_bode.setEnabled(False)
        
        self.worker = BodeSweepWorker(self.mgr, self.ui.bode_device.currentIndex(), self.ui.bode_start_f.value(), self.ui.bode_stop_f.value(), self.ui.bode_points.value(), self.ui.bode_amp.value(), self.ui.bode_gen_ch.currentIndex() + 1, self.ui.bode_osc_ch.currentIndex() + 1)
        self.worker.data_point.connect(self.on_data)
        self.worker.progress.connect(self.ui.bode_progress.setValue)
        self.worker.finished.connect(lambda: self.ui.btn_start_bode.setEnabled(True))
        self.worker.start()

    def on_data(self, freq, val):
        db = 20 * math.log10(max(val, 1e-6) / self.ui.bode_amp.value())
        self.main.bode_freqs.append(freq)
        self.main.bode_x.append(math.log10(freq))
        self.main.bode_y.append(db)
        self.main.bode_line.setData(self.main.bode_x, self.main.bode_y)

    def stop_sweep(self):
        if self.worker: self.worker.is_running = False