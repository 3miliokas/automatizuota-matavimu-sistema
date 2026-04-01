import csv
from datetime import datetime
import pyvisa
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer

from gui.ui_layout import Ui_MainWindow
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. UI Dizaino Inicijavimas
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)

        # 2. Vidiniai kintamieji
        self.x_data, self.y_data = [], []
        self.data_line = self.ui.graph_widget.plot(self.x_data, self.y_data, pen='y')
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_from_rigol)

        # 3. Signalų susiejimas (Events)
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

    # --- FUNKCIJOS ---

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
                
                if "SDG" in idn:
                    self.ui.combo_gen.addItem(f"{name} [{addr}]", addr)
                elif "DS1" in idn or "MSO" in idn:
                    self.ui.combo_osc.addItem(f"{name} [{addr}]", addr)
            except Exception:
                pass
                
        ports = serial.tools.list_ports.comports()
        for port in ports:
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
        except Exception as e:
            self.log_msg(f"Klaida atnaujinant generatorių: {e}")

    def trigger_autoscale(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.auto_scale()
            osc.close()
            self.log_msg("Rigol Auto-Scale iškviestas.")
        except Exception as e: self.log_msg(f"Klaida (Auto-Scale): {e}")

    def control_osc(self, state):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        try:
            osc = RigolMSO(addr)
            osc.run() if state == "run" else osc.stop()
            osc.close()
        except Exception as e: self.log_msg(f"Klaida (Run/Stop): {e}")

    def fetch_all_measurements(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: return
        
        was_streaming = self.timer.isActive()
        if was_streaming:
            self.timer.stop()

        self.log_msg("Skaitomi aparatūriniai matavimai...")
        try:
            osc = RigolMSO(addr)
            vpp = osc.get_measure("VPP")
            vmax = osc.get_measure("VMAX")
            vmin = osc.get_measure("VMIN")
            freq = osc.get_measure("FREQ")
            rise = osc.get_measure("RISetime")
            fall = osc.get_measure("FALLtime")
            osc.close()
            
            self.ui.lbl_meas_vpp.setText(f"Vpp: {self.format_eng(vpp, 'V')}")
            self.ui.lbl_meas_vmax.setText(f"Vmax: {self.format_eng(vmax, 'V')}")
            self.ui.lbl_meas_vmin.setText(f"Vmin: {self.format_eng(vmin, 'V')}")
            self.ui.lbl_meas_freq.setText(f"Dažnis: {self.format_eng(freq, 'Hz')}")
            self.ui.lbl_meas_rise.setText(f"Rise Time: {self.format_eng(rise, 's')}")
            self.ui.lbl_meas_fall.setText(f"Fall Time: {self.format_eng(fall, 's')}")
            self.log_msg("Matavimai sėkmingai atnaujinti.")
            
        except Exception as e: 
            self.log_msg(f"Klaida skaitant matavimus: {e}")

        if was_streaming:
            self.timer.start(500)

    def start_stream(self):
        if not self.ui.combo_osc.currentData():
            return self.log_msg("Klaida: Nepasirinktas oscilografas.")
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
        except pyvisa.errors.VisaIOError:
            pass 
        except Exception:
            pass

    def export_csv(self):
        if not self.x_data: return
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")
        if fn:
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Time", "Voltage"])
                for x, y in zip(self.x_data, self.y_data):
                    w.writerow([f"{x:.10e}", f"{y:.10e}"])
            self.log_msg("Eksportuota sėkmingai (Moksliniu formatu).")

    def save_rigol_screenshot(self):
        addr = self.ui.combo_osc.currentData()
        if not addr: 
            return self.log_msg("Klaida: Nepasirinktas oscilografas.")
        
        was_streaming = self.timer.isActive()
        if was_streaming:
            self.timer.stop()

        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti ekrano nuotrauką", "rigol_screen.png", "PNG failai (*.png)")
        if fn:
            self.log_msg("Nuskaitoma ekrano nuotrauka iš Rigol (tai gali užtrukti)...")
            try:
                osc = RigolMSO(addr)
                img_data = osc.get_screenshot()
                osc.close()
                
                with open(fn, "wb") as f:
                    f.write(img_data)
                self.log_msg(f"Nuotrauka sėkmingai išsaugota: {fn}")
            except Exception as e:
                self.log_msg(f"Klaida išsaugant nuotrauką: {e}")

        if was_streaming:
            self.timer.start(500)

    def fetch_tti(self, mode):
        port = self.ui.combo_tti.currentData()
        if not port:
            return self.log_msg("Klaida: Nepasirinktas TTi COM prievadas.")
            
        self.log_msg(f"Jungiamasi prie TTi 1604 ({port})...")
        try:
            tti = TTi1604(port)
            val = tti.get_voltage() if mode == "V" else tti.get_current()
            unit = "V" if mode == "V" else "A"
            tti.close()
            
            if val is not None:
                self.ui.lbl_tti_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
                self.log_msg(f"TTi matavimas: {self.format_eng(val, unit)}")
            else:
                self.ui.lbl_tti_res.setText("Reikšmė: Klaida (Timeout)")
                self.log_msg("Klaida: TTi neatsakė per nustatytą laiką.")
        except Exception as e:
            self.log_msg(f"Klaida komunikuojant su TTi: {e}")

    def fetch_escort(self, mode):
        port = self.ui.combo_escort.currentData()
        if not port:
            return self.log_msg("Klaida: Nepasirinktas Escort COM prievadas.")
            
        self.log_msg(f"Jungiamasi prie Escort 3136A ({port})...")
        try:
            escort = Escort3136A(port)
            val = escort.get_voltage_dc() if mode == "V" else escort.get_current_dc()
            unit = "V" if mode == "V" else "A"
            escort.close()
            
            if val is not None:
                self.ui.lbl_escort_res.setText(f"Reikšmė: {self.format_eng(val, unit)}")
                self.log_msg(f"Escort matavimas: {self.format_eng(val, unit)}")
            else:
                self.ui.lbl_escort_res.setText("Reikšmė: Nepavyko nuskaityti")
                self.log_msg("Klaida: Escort negrąžino tinkamo atsakymo.")
        except Exception as e:
            self.log_msg(f"Klaida komunikuojant su Escort: {e}")