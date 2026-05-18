import os
import csv
from datetime import datetime

def export_curves_csv(curves, filepath, logger=None):
    """
    Eksportuoja oscilografo realaus laiko grafikų (CH1-CH4) masyvus į CSV formatą.
    Kiekvienas matavimo taškas išsaugomas moksliniu (eksponentiniu) formatu (.10e),
    kad būtų išsaugotas maksimalus skaičiavimo tikslumas.
    """
    if not filepath: return
    try:
        with open(filepath, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Channel", "Time", "Voltage"])
            
            # Iteruojama per visus 4 oscilografo kanalus
            for ch in range(1, 5):
                if curves[ch].isVisible():
                    x_data, y_data = curves[ch].getData()
                    for x, y in zip(x_data, y_data): 
                        w.writerow([f"CH{ch}", f"{x:.10e}", f"{y:.10e}"])
        if logger: logger(f"CSV išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"Klaida eksportuojant CSV: {e}")

def export_bode_csv(freqs, gains, filepath, logger=None):
    """
    Eksportuoja amplitudės-dažnio charakteristikos (Bode) skenavimo rezultatus į CSV.
    """
    if not freqs or not filepath: return
    try:
        with open(filepath, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Frequency_Hz", "Gain_dB"])
            for f_hz, db in zip(freqs, gains): 
                w.writerow([f"{f_hz:.2f}", f"{db:.4f}"])
        if logger: logger(f"Bode CSV išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"Bode CSV klaida: {e}")

def generate_pdf_report(ui, bode_data, log_data, filepath, logger=None):
    """
    Sugeneruoja formalų PDF matavimų protokolą.
    Surenka generatoriaus parametrus, multimetrų rodmenis ir oscilografo matavimus.
    Grafikai (vektoriniai PyQtGraph objektai) paverčiami laikinais .png failais (rastrizuojami)
    ir integruojami į PDF dokumentą, po to ištrinami siekiant taupyti disko atmintį.
    """
    if not filepath: return
    try:
        from fpdf import FPDF
        import pyqtgraph.exporters
        
        # FPDF be papildomų šriftų geriausiai veikia su latin-1 koduote.
        # Ši funkcija pakeičia nepalaikomus simbolius (pvz. lietuviškas raides),
        # kad išvengtume UnicodeEncodeError kritinės klaidos generuojant ataskaitą.
        def sanitize(text):
            return text.encode('latin-1', 'replace').decode('latin-1')

        pdf = FPDF()
        pdf.add_page()
        
        # --- Ataskaitos antraštė ---
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=sanitize("Matavimu Protokolas"), ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=sanitize(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
        pdf.cell(200, 10, txt=sanitize(f"Bandomo prietaiso Serijos Nr.: {ui.input_serial.text()}"), ln=True)
        
        pdf.ln(5)
        
        # --- 1. Generatoriaus (SDG) būsena ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=sanitize("1. Generatoriaus Nustatymai (SDG):"), ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, txt=sanitize(f"Tipas: {ui.wave_type.currentText()}"), ln=True)
        pdf.cell(200, 8, txt=sanitize(f"Daznis: {ui.freq_in.value()} {ui.freq_unit.currentText()}"), ln=True)
        pdf.cell(200, 8, txt=sanitize(f"Amplitude: {ui.amp_in.value()} Vpp"), ln=True)
        
        pdf.ln(5)
        
        # --- 2. Multimetrų (TTi / Escort) būsena ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=sanitize("2. Multimetru Matavimai:"), ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, txt=sanitize(f"TTi 1604: {ui.lbl_tti_val.text()}"), ln=True)
        pdf.cell(200, 8, txt=sanitize(f"Escort 3136A: {ui.lbl_esc_val.text()}"), ln=True)

        pdf.ln(5)
        
        # --- 3. Oscilografo parametrų lentelė ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=sanitize("3. Oscilografo Parametrai:"), ln=True)
        pdf.set_font("Arial", size=10)
        
        has_measurements = False
        for i in range(ui.table_meas.rowCount()):
            item0 = ui.table_meas.item(i, 0)
            item1 = ui.table_meas.item(i, 1)
            val0 = item0.text() if item0 else ""
            val1 = item1.text() if item1 else ""
            
            # Įtraukiame tik matavimus, turinčius normalią reikšmę (ignoruojame tuščius '-')
            if val1 and val1 != "-":
                has_measurements = True
                pdf.cell(90, 8, txt=sanitize(val0), border=1)
                pdf.cell(90, 8, txt=sanitize(val1), border=1, ln=True)
                
        if not has_measurements:
            pdf.cell(200, 8, txt=sanitize("Nera nuskaitytu matavimu is lenteles."), ln=True)

        pdf.ln(5)
        
        # --- 4. Oscilograma (Laikino PNG failo generavimas ir integravimas) ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=sanitize("4. Oscilograma:"), ln=True)
        temp_img = "temp_plot.png"
        exporter = pyqtgraph.exporters.ImageExporter(ui.graph_widget.scene())
        exporter.export(temp_img)
        pdf.image(temp_img, x=10, w=190)
        os.remove(temp_img) # Šiukšlių valymas iš disko

        # --- 5. Bode diagrama ---
        bode_x, bode_y = bode_data
        if len(bode_x) > 0:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=sanitize("5. Amplitudes-Daznio Charakteristika (Bode):"), ln=True)
            temp_bode = "temp_bode.png"
            exporter_bode = pyqtgraph.exporters.ImageExporter(ui.bode_graph.scene())
            exporter_bode.export(temp_bode)
            pdf.image(temp_bode, x=10, w=190)
            os.remove(temp_bode)

        # --- 6. Logger diagrama ---
        log_x, log_y = log_data
        if len(log_x) > 0:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=sanitize("6. Ilgalaikio Registravimo Grafikas (Logger):"), ln=True)
            temp_log = "temp_log.png"
            exporter_log = pyqtgraph.exporters.ImageExporter(ui.log_graph.scene())
            exporter_log.export(temp_log)
            pdf.image(temp_log, x=10, w=190)
            os.remove(temp_log)

        pdf.output(filepath)
        if logger: logger(f"PDF išsaugotas: {filepath}")
    except Exception as e:
        if logger: logger(f"PDF klaida: {e}")