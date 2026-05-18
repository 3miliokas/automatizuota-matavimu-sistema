import time
import math
import csv
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

class BodeSweepWorker(QThread):
    """
    Foninė gija (Worker), skirta automatizuotam amplitudės-dažnio charakteristikos skenavimui.
    Vykdo ilgai trunkančius IO procesus (generatoriaus dažnio keitimą, pauzę pereinamiesiems
    procesams, ir atsakų skaitymą iš matuoklio), neblokuodama pagrindinės grafinės vartotojo
    sąsajos (GUI) gijos.
    """
    
    # Signalai (PyQt Signals), užtikrinantys saugų duomenų perdavimą iš foninės gijos į GUI.
    # Neleidžia kilti sinchronizacijos klaidoms (Race conditions) braižant grafikus.
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
        """Pagrindinis foninės gijos ciklas. Vykdomas automatiškai iškvietus .start() metodą."""
        try:
            with self.mgr.lock: # Mutex užraktas magistralės apsaugai
                if not self.mgr.gen: raise Exception("Generatorius neprijungtas.")
                self.mgr.gen.set_output(True, self.gen_ch)

            # Sugeneruojamas logaritminis dažnių masyvas naudojant numpy
            freqs = np.logspace(math.log10(self.start_f), math.log10(self.stop_f), self.points)
            
            for i, f in enumerate(freqs):
                # Patikrinama vėliavėlė, leidžianti operatoriui saugiai nutraukti procesą
                if not self.is_running: break
                
                # Išsiunčiamas naujas dažnis į generatorių
                with self.mgr.lock:
                    self.mgr.gen.apply_waveform("SINE", "FRQ", f, "AMP", self.amp, 0, 0, 50, 50, 0, 0, 0, self.gen_ch)
                
                # Suskaidytas laukimas (Chunked sleeping).
                # Suteikia grandinei 0.5 s laiko nusistovėti po dažnio pakeitimo.
                # Laukimas skaidomas po 0.05 s, kad gija galėtų momentaliai reaguoti į "STOP" komandą,
                # neįstrigdama viename ilgame time.sleep() bloke.
                wait_time = 0.5
                elapsed = 0
                while elapsed < wait_time and self.is_running:
                    time.sleep(0.05)
                    elapsed += 0.05
                    
                if not self.is_running: break
                
                # Nuskaitomi matavimai iš vartotojo pasirinkto prietaiso
                val = None
                with self.mgr.lock: # Saugus duomenų surinkimas
                    if self.dev_idx == 0 and self.mgr.osc:
                        val = self.mgr.osc.get_measure("VPP", channel=self.osc_ch)
                    elif self.dev_idx == 1 and self.mgr.tti:
                        res = self.mgr.tti.get_reading()
                        if res: val = res[0]
                    elif self.dev_idx == 2 and self.mgr.esc:
                        val = self.mgr.esc.read_value()

                # Surinktas duomenų taškas perduodamas į GUI signalo pagalba
                if val is not None:
                    self.data_point.emit(float(f), float(val))
                self.progress.emit(int((i + 1) / self.points * 100))

            # Saugus generatoriaus išjungimas po skenavimo
            with self.mgr.lock:
                if self.mgr.gen: self.mgr.gen.set_output(False, self.gen_ch)
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


class DataLoggerWorker(QThread):
    """
    Foninė gija, skirta autonomiškam, ilgalaikiam duomenų registravimui.
    Periodiškai skaito multimetrų (TTi arba Escort) parodymus ir realiu laiku
    rašo juos į išorinį CSV failą diske, neapkraudama kompiuterio operatyviosios atminties.
    """
    
    data_point = pyqtSignal(float, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager, dev_idx, mode_idx, interval_ms, duration_mins, filepath):
        super().__init__()
        self.mgr = manager
        self.dev_idx = dev_idx
        self.mode_idx = mode_idx
        
        # Konvertuojama į sekundes sistemos skaičiavimams
        self.interval_secs = interval_ms / 1000.0
        self.duration_secs = duration_mins * 60
        self.filepath = filepath
        self.is_running = True

    def run(self):
        try:
            # Duomenų failas atidaromas rašymo ('w') režimu. CSV modulis užtikrina 
            # korektišką atskyrimą ir išdėstymą stulpeliais.
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time_s", "Value"])
                start_time = time.time()
                
                while self.is_running:
                    t_elapsed = time.time() - start_time
                    
                    # Jei trukmė apibrėžta (> 0) ir viršyta, stabdomas ciklas
                    if self.duration_secs > 0 and t_elapsed > self.duration_secs:
                        break

                    val = 0.0
                    
                    # Abipusės atskirties (Mutex) užraktas prieš komunikuojant su aparatine įranga
                    with self.mgr.lock:
                        if self.dev_idx == 0 and self.mgr.tti: 
                            res = self.mgr.tti.get_reading()
                            val = res[0] if (res and res[0] is not None) else 0.0
                        elif self.dev_idx == 1 and self.mgr.esc:
                            val = self.mgr.esc.read_value() or 0.0

                    # Duomenys realiu laiku išsaugomi į diską moksliniu (eksponentiniu) formatu
                    writer.writerow([f"{t_elapsed:.2f}", f"{val:.6e}"])
                    f.flush() # Priverstinis iškrovimas į diską išvengiant duomenų praradimo lūžio metu
                    
                    # Duomenys perduodami GUI grafikų atnaujinimui
                    self.data_point.emit(float(t_elapsed), float(val))
                    
                    # Suskaidytas laukimas reagavimui į stabdymo mygtuką
                    wait_start = time.time()
                    while (time.time() - wait_start) < self.interval_secs and self.is_running:
                        time.sleep(0.05)
                        
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))