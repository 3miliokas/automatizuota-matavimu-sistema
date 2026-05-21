import time
import math
import csv
import os
from PyQt6.QtCore import QThread, pyqtSignal

class BodeSweepWorker(QThread):
    """
    Foninė gija, atliekanti automatinį Bode (Amplitudės-Dažnio charakteristikos) skenavimą.
    Veikia atskirai nuo GUI, valdo generatoriaus dažnių perjungimą ir
    sinchroniškai nuskaito matavimų rezultatus iš pasirinktų matuoklių.
    """
    data_point = pyqtSignal(float, dict)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager, targets, start_f, stop_f, points, amp, gen_ch):
        super().__init__()
        self.mgr = manager
        self.targets = targets
        self.start_f = start_f
        self.stop_f = stop_f
        self.points = points
        self.amp = amp
        self.gen_ch = gen_ch
        self.is_running = True

    def run(self):
        temp_csv_path = "temp_bode_autosave.csv"
        try:
            # 1. PIRMINĖ APARATŪROS KONFIGŪRACIJA FONE
            with self.mgr.lock:
                if not self.mgr.gen: 
                    raise Exception("Generatorius neprijungtas.")
                
                try:
                    if hasattr(self.mgr.gen, 'instr'):
                        self.mgr.gen.instr.write(f"C{self.gen_ch}:OUTP LOAD,HZ")
                except:
                    pass
                self.mgr.gen.set_output(True, self.gen_ch)

                if self.targets.get("tti") and self.mgr.tti:
                    self.mgr.tti.execute_macro(["V", "AC", "AUTO"])
                
                if self.targets.get("escort") and self.mgr.esc:
                    self.mgr.esc.send_command("S110")
                    time.sleep(1.0)
            
            time.sleep(0.5)

            # 2. DAŽNIŲ TINKLELIO KŪRIMAS
            freqs = []
            if self.points > 1:
                ratio = (self.stop_f / self.start_f) ** (1.0 / (self.points - 1))
                freqs = [self.start_f * (ratio ** i) for i in range(self.points)]
            else:
                freqs = [self.start_f]
            
            # 3. MATAVIMŲ CIKLAS SU LAIKINU SAUGOJIMU (Autosave)
            with open(temp_csv_path, 'w', newline='') as f_csv:
                writer = csv.writer(f_csv)
                
                header = ["Freq_Hz"]
                if self.targets.get("rigol"): 
                    header.extend([f"Rigol_CH{ch}_V" for ch in self.targets["rigol"]])
                if self.targets.get("tti"): 
                    header.append("TTi_1604_V")
                if self.targets.get("escort"): 
                    header.append("Escort_V")
                writer.writerow(header)

                for i, f in enumerate(freqs):
                    if not self.is_running: break
                    
                    # Generuojame naują dažnį
                    with self.mgr.lock:
                        self.mgr.gen.apply_waveform("SINE", "FRQ", f, "AMP", self.amp, 0, 0, 50, 50, 0, 0, 0, self.gen_ch)
                    
                    wait_time = max(0.2, 5.0 / f) 
                    elapsed = 0
                    while elapsed < wait_time and self.is_running:
                        time.sleep(0.05)
                        elapsed += 0.05
                        
                    if not self.is_running: break

                    results = {}
                    csv_row = [f"{f:.2f}"]

                    # Nuskaitymas iš Rigol MSO
                    if self.targets.get("rigol") and self.mgr.osc:
                        with self.mgr.lock:
                            # 1. PIRMINIS AUTOSCALE (Tik pačiam pirmiems taškui)
                            if i == 0:
                                if hasattr(self.mgr.osc, 'send_command'):
                                    self.mgr.osc.send_command(":AUToscale")
                                else:
                                    self.mgr.osc.write(":AUToscale")
                                time.sleep(12.0)

                            # 2. DINAMINIS 1-2-5 LAIKO AŠIES SKAIČIAVIMAS
                            # Oscilografas priima tik 1, 2, 5 žingsnius (pvz. 1ms, 2ms, 5ms).
                            # Norime matyti ~3 periodus ekrane. (10 padalų ekranas)
                            ideal_timebase = (3.0 / f) / 10.0 
                            exponent = math.floor(math.log10(ideal_timebase))
                            mantissa = ideal_timebase / (10 ** exponent)
                            
                            if mantissa < 2.0: snap = 1.0
                            elif mantissa < 5.0: snap = 2.0
                            else: snap = 5.0
                            
                            rigol_timebase = snap * (10 ** exponent)
                            
                            # Siunčiame suapvalintą laiko ašį
                            if hasattr(self.mgr.osc, 'send_command'):
                                self.mgr.osc.send_command(f":TIMebase:MAIN:SCALe {rigol_timebase:.2e}")
                            else:
                                self.mgr.osc.write(f":TIMebase:MAIN:SCALe {rigol_timebase:.2e}")
                                
                            time.sleep(4) # Palaukiam, kol oscilografas pritaikys naują ašį

                            # 3. MATAVIMAS
                            for ch in self.targets["rigol"]:
                                try:
                                    val = self.mgr.osc.get_measure("VRMS", channel=ch)
                                    if val is not None and val < 1000:
                                        results[f"Rigol CH{ch}"] = val
                                        csv_row.append(f"{val:.6e}")
                                    else:
                                        results[f"Rigol CH{ch}"] = 1e-6
                                        csv_row.append("1e-06")
                                except:
                                    results[f"Rigol CH{ch}"] = 1e-6
                                    csv_row.append("1e-06")
                                    
                    # Nuskaitymas iš TTi 1604
                    if self.targets.get("tti") and self.mgr.tti:
                        with self.mgr.lock:
                            val, unit, mode = self.mgr.tti.get_reading(timeout=1.0)
                            if val is not None and val != float('inf') and "V" in unit:
                                results["TTi 1604"] = val
                                csv_row.append(f"{val:.6e}")
                            else:
                                results["TTi 1604"] = 1e-6
                                csv_row.append("1e-06")

                    # Nuskaitymas iš Escort 3136A
                    if self.targets.get("escort") and self.mgr.esc:
                        with self.mgr.lock:
                            val = self.mgr.esc.read_value()
                            if val is not None:
                                results["Escort"] = val
                                csv_row.append(f"{val:.6e}")
                            else:
                                results["Escort"] = 1e-6
                                csv_row.append("1e-06")

                    writer.writerow(csv_row)
                    f_csv.flush()
                    os.fsync(f_csv.fileno())

                    self.data_point.emit(float(f), results)
                    self.progress.emit(int(((i + 1) / self.points) * 100))

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


class DataLoggerWorker(QThread):
    """
    Foninė gija, atliekanti ilgalaikį duomenų fiksavimą (Data Logging) nurodytu intervalu.
    """
    data_point = pyqtSignal(float, float)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager, dev_idx, mode_txt, interval_ms, duration_secs, filepath, osc_channel=1):
        super().__init__()
        self.mgr = manager
        self.dev_idx = dev_idx
        self.mode_txt = mode_txt
        self.interval_secs = interval_ms / 1000.0
        self.duration_secs = duration_secs
        self.filepath = filepath
        self.osc_channel = osc_channel 
        self.is_running = True

    def run(self):
        try:
            import os
            import time
            import math
            import csv
            
            # 1. PIRMINIS PRIETAISŲ KONFIGŪRAVIMAS FONE
            with self.mgr.lock:
                
                # Jeigu matuosime su Rigol, automatiškai susikalibruojame
                if self.dev_idx == 0 and self.mgr.osc:
                    if hasattr(self.mgr.osc, 'send_command'):
                        self.mgr.osc.send_command(":AUToscale")
                    else:
                        try: self.mgr.osc.write(":AUToscale")
                        except: pass
                    
                    # Saugus *OPC? patikrinimas apsisaugant nuo PyVISA AttributeError
                    try:
                        instr_obj = getattr(self.mgr.osc, 'inst', getattr(self.mgr.osc, 'instr', None))
                        if instr_obj:
                            old_timeout = instr_obj.timeout
                            instr_obj.timeout = 10000 
                            self.mgr.osc.query("*OPC?") 
                            instr_obj.timeout = old_timeout
                        else:
                            time.sleep(3.5)
                    except:
                        time.sleep(3.5)      

                # TTi konfigūravimas
                if self.dev_idx == 1 and self.mgr.tti:
                    cmds = []
                    if "V" in self.mode_txt: cmds.append("V")
                    if "A" in self.mode_txt and "mA" not in self.mode_txt: cmds.append("A")
                    if "mA" in self.mode_txt: cmds.append("mA")
                    if "OHM" in self.mode_txt: cmds.append("OHM")
                    if "Hz" in self.mode_txt: cmds.extend(["AC", "FREQ"])
                    elif "DC" in self.mode_txt: cmds.append("DC")
                    elif "AC" in self.mode_txt: cmds.append("AC")
                    self.mgr.tti.execute_macro(cmds) 
                        
                # Escort konfigūravimas
                elif self.dev_idx == 2 and self.mgr.esc:
                    esc_cmds = {"V DC": "S100", "V AC": "S110", "Ω": "S120", "A DC": "S140", "A AC": "S150", "Hz": "S170", "dBm": "S1B0", "Continuity": "S1A0", "Diode": "S160"}
                    if self.mode_txt in esc_cmds:
                        self.mgr.esc.send_command(esc_cmds[self.mode_txt])
                        time.sleep(1.0)
                        self.mgr.esc.read_measurement()

            # 2. ILGALAIKIO RAŠYMO CIKLAS
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
                        if self.dev_idx == 0 and self.mgr.osc:
                            try:
                                raw_val = self.mgr.osc.get_measure(self.mode_txt, channel=self.osc_channel)
                                if raw_val is not None:
                                    val = float(raw_val)
                                    if val >= 1e15 or math.isnan(val) or math.isinf(val):
                                        val = 0.0
                            except:
                                val = 0.0
                                
                        elif self.dev_idx == 1 and self.mgr.tti: 
                            try:
                                res = self.mgr.tti.get_reading()
                                val = float(res[0]) if (res and res[0] is not None) else 0.0
                            except:
                                val = 0.0
                                
                        elif self.dev_idx == 2 and self.mgr.esc:
                            try:
                                val = float(self.mgr.esc.read_value() or 0.0)
                            except:
                                val = 0.0

                    writer.writerow([f"{t_elapsed:.2f}", f"{val:.6e}"])
                    f.flush()
                    os.fsync(f.fileno()) # Priverčia OS iš karto išsaugoti diskelyje
                    
                    self.data_point.emit(float(t_elapsed), float(val))
                    
                    if self.duration_secs > 0:
                        pct = int((t_elapsed / self.duration_secs) * 100)
                        self.progress.emit(min(pct, 100))
                    
                    wait_start = time.time()
                    while (time.time() - wait_start) < self.interval_secs and self.is_running:
                        time.sleep(0.05)
                        
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))