import os
import csv
from datetime import datetime

def export_curves_csv(curves, filepath, logger=None):
    """
    Išsaugo oscilografo aktyvių kanalų (kreivių) duomenis į CSV failą.
    Kiekviena eilutė atitinka: Kanalą, Laiką (s), Įtampą (V).
    """
    if not filepath: return
    try:
        with open(filepath, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Channel", "Time", "Voltage"])
            
            # Pereina per visus galimus 4 oscilografo kanalus
            for ch in range(1, 5):
                # Eksportuojami tik tie kanalai, kurie šiuo metu rodomi ekrane
                if curves[ch].isVisible():
                    x_data, y_data = curves[ch].getData()
                    # ZIP funkcija apjungia atskirus X ir Y masyvus į porų iteratorių
                    for x, y in zip(x_data, y_data): 
                        # Naudojamas eksponentinis formatavimas dideliam tikslumui
                        w.writerow([f"CH{ch}", f"{x:.10e}", f"{y:.10e}"])
                        
        if logger: logger(f"CSV išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"Klaida eksportuojant CSV: {e}")

def export_bode_csv(freqs, plot_data, filepath, logger=None):
    """
    Išsaugo Bode (Amplitudės-Dažnio Charakteristikos) diagramos duomenis į CSV failą.
    Dinamiškai palaiko neribotą kiekį prietaisų ir kanalų.
    """
    if not freqs or not filepath or not plot_data: return
    try:
        with open(filepath, 'w', newline='') as f:
            w = csv.writer(f)
            
            # Dinaminis antraščių (Headers) generavimas pagal aktyvius matuoklius
            headers = ["Frequency_Hz"]
            device_names = list(plot_data.keys())
            for name in device_names:
                headers.append(f"{name}_Gain_dB")
            w.writerow(headers)
            
            # Iteruojame per visus dažnio taškus ir surenkame kiekvieno prietaiso dB reikšmę
            for i, f_hz in enumerate(freqs):
                row = [f"{f_hz:.2f}"]
                for name in device_names:
                    db_list = plot_data[name][1] # Paimame Y (dB) ašies duomenų sąrašą
                    if i < len(db_list):
                        row.append(f"{db_list[i]:.4f}")
                    else:
                        row.append("") # Apsauga, jei dėl ryšio klaidos trūktų taško
                w.writerow(row)
                
        if logger: logger(f"Bode CSV išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"Bode CSV klaida: {e}")
        
def generate_pdf_report(ui, bode_data, log_data, options, filepath, logger=None, osc_instr=None):
    """
    Sukuria ir išsaugo išsamią PDF ataskaitą apie atliktus matavimus.
    Dokumentas konstruojamas pagal vartotojo pasirinkimus (options),
    paverčiant GUI grafikų objektus į laikinus paveikslėlius ir įterpiant
    juos į galutinį PDF failą, naudojant FPDF biblioteką.
    """
    if not filepath: return
    try:
        from fpdf import FPDF
        import pyqtgraph.exporters
        
        def sanitize(text):
            """
            Išvalo tekstą nuo ASCII kontrolinių simbolių ir netinkamų znakų
            (ypač grąžinamų iš oscilografo), kurie galėtų "nulaužti" PDF generatorių.
            """
            clean_text = text.replace('\r', '').replace('\n', '').replace('$', '').replace('~', ' ')
            return clean_text.encode('latin-1', 'replace').decode('latin-1')

        pdf = FPDF()
        pdf.add_page()
        
        # --- ANTRAŠTĖ IR METADUOMENYS ---
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=sanitize("Matavimu Protokolas"), ln=True, align='C')
        
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 6, txt=sanitize(f"Sukurta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
        pdf.cell(200, 6, txt=sanitize(f"Irenginio Serijos Nr.: {ui.input_serial.text()}"), ln=True)
        
        notes = options.get("notes", "")
        if notes:
            pdf.set_font("Arial", 'I', 11)
            pdf.cell(200, 8, txt=sanitize(f"Pastabos: {notes}"), ln=True)
            
        pdf.ln(5)
        
        # --- 1. GENERATORIAUS BŪSENA ---
        if options.get("gen", True):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("1. Generatoriaus Parametrai (UI Konfiguracija):"), ln=True)
            
            pdf.set_font("Arial", size=10)
            ch1_stat = "ON" if ui.btn_gen_ch1.isChecked() else "OFF"
            ch2_stat = "ON" if ui.btn_gen_ch2.isChecked() else "OFF"
            pdf.cell(190, 8, txt=sanitize(f"Aktyvus kanalai: CH1 [{ch1_stat}] | CH2 [{ch2_stat}]"), border=1, ln=True, align='C')
            
            # Parametrų lentelė
            pdf.cell(63, 8, txt=sanitize(f"Forma: {ui.wave_type.currentText()}"), border=1)
            pdf.cell(63, 8, txt=sanitize(f"Daznis: {ui.freq_in.value()} {ui.freq_unit.currentText()}"), border=1)
            pdf.cell(64, 8, txt=sanitize(f"Amplitude: {ui.amp_in.value()} V"), border=1, ln=True)
            
            pdf.cell(63, 8, txt=sanitize(f"Poslinkis: {ui.offset_in.value()} V"), border=1)
            pdf.cell(63, 8, txt=sanitize(f"Faze: {ui.phase_in.value()} deg"), border=1)
            pdf.cell(64, 8, txt=sanitize(f"Duty: {ui.duty_in.value()} %"), border=1, ln=True)
            
            pdf.cell(95, 8, txt=sanitize(f"Simetrija: {ui.sym_in.value()} %"), border=1)
            pdf.cell(95, 8, txt=sanitize(f"Uzdelsimas: {ui.delay_in.value()} s"), border=1, ln=True)
            pdf.ln(5)
            
        # --- 2. MULTIMETRAI ---
        if options.get("multi", True):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("2. Multimetru Fiksuotos Reiksmes:"), ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(95, 8, txt=sanitize(f"TTi 1604: {ui.lbl_tti_val.text()}"), border=1)
            pdf.cell(95, 8, txt=sanitize(f"Escort 3136A: {ui.lbl_esc_val.text()}"), border=1, ln=True)
            pdf.ln(5)
            
        # --- 3. OSCILOGRAFAS (AUTOMATINIAI MATAVIMAI) ---
        if options.get("osc_table", True):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("3. Oscilografo Automatiniai Matavimai:"), ln=True)
            pdf.set_font("Arial", size=10)
            
            active_osc = [ch for ch in ["CH1", "CH2", "CH3", "CH4"] 
                          if getattr(ui, f"btn_osc_{ch.lower()}").isChecked()]
            
            pdf.cell(190, 8, txt=sanitize(f"Ekrane aktyvus kanalai: {', '.join(active_osc) if active_osc else 'Nera'}"), ln=True)
            
            param_map = {
                "VPP": ("Vpp", "V"), "VMAX": ("Vmax", "V"), "VMIN": ("Vmin", "V"), 
                "VAMP": ("Vamp", "V"), "VTOP": ("Vtop", "V"), "VBASE": ("Vbase", "V"), 
                "VAVG": ("Vavg", "V"), "VRMS": ("Vrms", "V"), "OVERshoot": ("Overshoot", "%"), 
                "FREQuency": ("Freq", "Hz"), "PERiod": ("Period", "s"), "RTIMe": ("Rise Time", "s"), 
                "FTIMe": ("Fall Time", "s"), "PPULse": ("Pulse (+)", "s"), "NPULse": ("Pulse (-)", "s"), 
                "PDUTy": ("Duty (+)", "%"), "NDUTy": ("Duty (-)", "%")
            }
            
            for ch in active_osc:
                ch_num = ch.replace("CH", "")
                pdf.ln(2)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(190, 8, txt=sanitize(f"{ch}:"), ln=True)
                pdf.set_font("Arial", size=10)
                
                for scpi_cmd, (display_name, unit) in param_map.items():
                    val_str = "N/A"
                    if osc_instr:
                        try:
                            # Nuskaitome iš oscilografo
                            val = osc_instr.query(f":MEASure:ITEM? {scpi_cmd},CHANnel{ch_num}").strip()
                            if val and "9.9" not in val: # Rigol meta 9.9E37, kai nesugeba išmatuoti
                                val_float = float(val)
                                val_str = f"{val_float:.4e} {unit}"
                        except:
                            pass
                    
                    # Atspausdinama švariu sąrašu be rėmelių (border=0)
                    pdf.cell(35, 6, txt=sanitize(display_name), border=0)
                    pdf.cell(155, 6, txt=sanitize(val_str), border=0, ln=True)
            pdf.ln(5)

        # --- 4. OSCILOGRAMA ---
        if options.get("osc_graph", True):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("4. Oscilograma (Signalai Realiu Laiku):"), ln=True)
            
            # Sukuriamas laikinas paveikslėlis iš grafiko widgeto
            temp_img = "temp_plot.png"
            exporter = pyqtgraph.exporters.ImageExporter(ui.graph_widget.scene())
            exporter.export(temp_img)
            
            # Įterpiamas į PDF ir iškart ištrinamas iš laikmenos
            pdf.image(temp_img, x=10, w=190)
            os.remove(temp_img)
            pdf.add_page() # Lūžis (naujas lapas) po oscilogramos
            
        # --- 5. BODE ---
        if options.get("bode", True):
            bode_x, bode_y = bode_data
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("5. Amplitudes-Daznio Charakteristika (Bode Analize):"), ln=True)
            
            # Bode Metaduomenys
            pdf.set_font("Arial", size=9)
            pdf.cell(190, 6, txt=sanitize(f"Skenavimo ruozas: nuo {ui.bode_start_f.value()} {ui.bode_start_unit.currentText()} iki {ui.bode_stop_f.value()} {ui.bode_stop_unit.currentText()} | Tasku sk.: {ui.bode_points.value()} | Gen. Amplitude: {ui.bode_amp.value()} V"), ln=True)
            
            # Atvaizduojamas Bode grafikas taip pat kaip Oscilograma
            temp_bode = "temp_bode.png"
            exporter_bode = pyqtgraph.exporters.ImageExporter(ui.bode_graph.scene())
            exporter_bode.export(temp_bode)
            pdf.image(temp_bode, x=10, w=190)
            os.remove(temp_bode)
            pdf.ln(5)
            
        # --- 6. LOGGER ---
        if options.get("log", True):
            log_x, log_y = log_data
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("6. Ilgalaikio Registravimo Grafikas (Logger):"), ln=True)
            
            pdf.set_font("Arial", size=9)
            pdf.cell(190, 6, txt=sanitize(f"Skenavimo saltinis: {ui.log_device.currentText()} ({ui.log_mode.currentText()}) | Intervalas: {ui.log_interval.value()} {ui.log_interval_unit.currentText()} | Trukme: {ui.log_duration.value()} {ui.log_duration_unit.currentText()}"), ln=True)
            
            # Logger grafiko konversija ir atvaizdavimas
            temp_log = "temp_log.png"
            exporter_log = pyqtgraph.exporters.ImageExporter(ui.log_graph.scene())
            exporter_log.export(temp_log)
            pdf.image(temp_log, x=10, w=190)
            os.remove(temp_log)
            pdf.ln(5)

        # --- 7. FFT ---
        if options.get("fft", True):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, txt=sanitize("7. Greitoji Furje Transformacija (FFT):"), ln=True)
            
            pdf.set_font("Arial", size=9)
            pdf.cell(190, 6, txt=sanitize(ui.lbl_fft_peak.text()), ln=True)
            
            # FFT grafiko konversija ir atvaizdavimas
            temp_fft = "temp_fft.png"
            exporter_fft = pyqtgraph.exporters.ImageExporter(ui.fft_graph.scene())
            exporter_fft.export(temp_fft)
            pdf.image(temp_fft, x=10, w=190)
            os.remove(temp_fft)

        # Išsaugojamas galutinis pdf failas
        pdf.output(filepath)
        if logger: logger(f"PDF išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"PDF klaida: {e}")