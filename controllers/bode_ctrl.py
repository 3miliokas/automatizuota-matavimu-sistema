import math
from core.workers import BodeSweepWorker

class BodeController:
    """
    Amplitudės ir dažnio charakteristikos (Bode diagramos) valdymo valdiklis.
    Susieja grafinės vartotojo sąsajos elementus su fonine skenavimo gija (BodeSweepWorker)
    bei atlieka matavimų konvertavimą į logaritminę decibelų (dB) skalę.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        self.worker = None
        
        # Mygtukų signalų susiejimas su funkcijomis
        self.ui.btn_start_bode.clicked.connect(self.start_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_sweep)

    def start_sweep(self):
        """
        Inicijuoja automatinio skenavimo procesą.
        Paruošia grafinę aplinką, blokuoja įvestis ir paleidžia foninę giją.
        """
        # Perjungiama į Bode grafiko skirtuką
        self.ui.graph_tabs.setCurrentIndex(1)
        
        # Jei veikia oscilografo tiesioginis atvaizdavimas, jį būtina sustabdyti,
        # kad išvengtume magistralės perkrovos ir konfliktų
        if hasattr(self.main.osc_ctrl, 'stream_timer') and self.main.osc_ctrl.stream_timer.isActive():
            self.ui.btn_stream.setChecked(False)
        
        # Išvalomi seni matavimų duomenys ir grafiko kreivė
        self.main.bode_freqs.clear()
        self.main.bode_x.clear()
        self.main.bode_y.clear()
        self.main.bode_line.setData([], [])
        
        self.ui.btn_start_bode.setEnabled(False)
        
        # Sukuriama ir parametrizuojama foninė skenavimo gija
        self.worker = BodeSweepWorker(
            self.mgr, 
            self.ui.bode_device.currentIndex(), 
            self.ui.bode_start_f.value(), 
            self.ui.bode_stop_f.value(), 
            self.ui.bode_points.value(), 
            self.ui.bode_amp.value(), 
            self.ui.bode_gen_ch.currentIndex() + 1, 
            self.ui.bode_osc_ch.currentIndex() + 1
        )
        
        # Gijos signalų (įvykių) susiejimas su GUI atnaujinimo funkcijomis
        self.worker.data_point.connect(self.on_data)
        self.worker.progress.connect(self.ui.bode_progress.setValue)
        self.worker.finished.connect(lambda: self.ui.btn_start_bode.setEnabled(True))
        
        self.worker.start()

    def on_data(self, freq, val):
        """
        Apdoroja kiekvieną iš foninės gijos gautą matavimo tašką.
        Apskaičiuoja stiprinimą/slopinimą decibelais ir atnaujina grafiką.
        """
        # Apskaičiuojamas stiprinimas decibelais: 20 * log10(V_out / V_in).
        # max(val, 1e-6) apsaugo nuo matematinės klaidos (log(0) neegzistuoja),
        # jei išmatuota amplitudė visiškai lygi nuliui.
        db = 20 * math.log10(max(val, 1e-6) / self.ui.bode_amp.value())
        
        self.main.bode_freqs.append(freq)
        self.main.bode_x.append(math.log10(freq)) # X ašis atvaizduojama logaritmine skale
        self.main.bode_y.append(db)
        
        # Braižoma nauja kreivė
        self.main.bode_line.setData(self.main.bode_x, self.main.bode_y)

    def stop_sweep(self):
        """Nutraukia aktyvų skenavimo procesą pakeičiant gijos vėliavėlę."""
        if self.worker: 
            self.worker.is_running = False