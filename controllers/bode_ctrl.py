import math
from PyQt6.QtWidgets import QMessageBox
from core.workers import BodeSweepWorker
import pyqtgraph as pg

class BodeController:
    """
    Amplitudės ir Dažnio Charakteristikos (Bode diagramos) valdiklis.
    Ši klasė surenka nustatymus iš GUI, validuoja vartotojo įvestį ir
    paleidžia asimetrinę foninę giją (BodeSweepWorker), skirtą atlikti
    automatinį sinchroninį įrenginių skenavimą.
    """
    def __init__(self, main, ui, mgr):
        self.main = main
        self.ui = ui
        self.mgr = mgr
        self.worker = None
        
        # Žodynas, skirtas saugoti PyQtGraph kreivių objektus skirtingiems prietaisams/kanalams
        self.bode_curves = {}
        
        # UI mygtukų susiejimas
        self.ui.btn_start_bode.clicked.connect(self.start_sweep)
        self.ui.btn_stop_bode.clicked.connect(self.stop_sweep)

    def start_sweep(self):
        """
        Pagrindinė skenavimo inicijavimo funkcija.
        Atlieka griežtą techninės įrangos būsenos ir įvesties validaciją prieš blokuojant sistemą.
        """
        # 1. GENERATORIAUS PATIKRA
        # Be generatoriaus skenavimas yra fiziškai neįmanomas.
        if not self.mgr.gen:
            QMessageBox.critical(self.main, "Klaida", "Neprijungtas Siglent generatorius! Skenavimas negalimas.")
            return

        # 2. PRIETAISŲ PATIKRA
        use_rigol = self.ui.cb_bode_rigol.isChecked()
        use_tti = self.ui.cb_bode_tti.isChecked()
        use_escort = self.ui.cb_bode_escort.isChecked()
        
        if not (use_rigol or use_tti or use_escort):
            QMessageBox.warning(self.main, "Dėmesio", "Nepasirinktas nei vienas matavimo prietaisas!")
            return

        # Užtikriname, kad varnele pažymėti prietaisai tikrai turi gyvą VISA/COM ryšį
        if use_rigol and not self.mgr.osc:
            QMessageBox.critical(self.main, "Klaida", "Pasirinktas Rigol MSO, bet jis nėra prijungtas!")
            return
        if use_tti and not self.mgr.tti:
            QMessageBox.critical(self.main, "Klaida", "Pasirinktas TTi 1604, bet jis nėra prijungtas!")
            return
        if use_escort and not self.mgr.esc:
            QMessageBox.critical(self.main, "Klaida", "Pasirinktas Escort 3136A, bet jis nėra prijungtas!")
            return

        # 3. RIGOL KANALŲ PATIKRA
        active_osc_channels = []
        if use_rigol:
            if self.ui.cb_bode_ch1.isChecked(): active_osc_channels.append(1)
            if self.ui.cb_bode_ch2.isChecked(): active_osc_channels.append(2)
            if self.ui.cb_bode_ch3.isChecked(): active_osc_channels.append(3)
            if self.ui.cb_bode_ch4.isChecked(): active_osc_channels.append(4)
            
            if not active_osc_channels:
                QMessageBox.warning(self.main, "Dėmesio", "Pasirinktas Rigol MSO, bet nepažymėtas nei vienas matavimo kanalas!")
                return

        # 4. DAŽNIO SKAIČIAVIMAS
        # Konvertuojame vartotojo įvestį iš kHz/MHz į bazinius SI vienetus (Hz)
        unit_multipliers = {"Hz": 1, "kHz": 1e3, "MHz": 1e6}
        start_f = self.ui.bode_start_f.value() * unit_multipliers[self.ui.bode_start_unit.currentText()]
        stop_f = self.ui.bode_stop_f.value() * unit_multipliers[self.ui.bode_stop_unit.currentText()]

        if start_f >= stop_f:
            QMessageBox.warning(self.main, "Klaida", "Pradinis dažnis turi būti mažesnis už galinį!")
            return

        # 5. UI PARUOŠIMAS
        # Perjungiame programą į "Bode" grafikų tabą
        self.ui.graph_tabs.setCurrentIndex(1)
        
        # Priverstinai išjungiame oscilografo Live-Stream, jei jis veikia,
        # kad USB magistralė nebūtų apkrauta siunčiant komandas
        if hasattr(self.main.osc_ctrl, 'stream_timer') and self.main.osc_ctrl.stream_timer.isActive():
            self.ui.btn_stream.setChecked(False)
            
        # Išvalome senus duomenis iš atminties ir ekrano
        self.ui.bode_graph.clear()
        self.main.bode_freqs.clear()
        self.main.bode_y.clear() 
        
        # Braižymo spalvų paletė
        colors = ['#00FFFF', '#FF00FF', '#00FF00', '#FFFF00', '#FFA500', '#FFFFFF']
        color_idx = 0
        
        self.bode_curves = {}
        self.plot_data = {} 
        
        # Suformuojame žodyną (konfigūraciją), kurį perduosime gijai
        target_config = {"rigol": active_osc_channels if use_rigol else [], "tti": use_tti, "escort": use_escort}
        
        # Sukuriame atskiras kreives kiekvienam matavimo aparatui/kanalui
        if use_tti:
            self.bode_curves["TTi 1604"] = self.ui.bode_graph.plot(pen=pg.mkPen(color=colors[color_idx], width=1.5), name="TTi 1604", symbol='o', symbolSize=5)
            self.plot_data["TTi 1604"] = ([], []) # (X_list, Y_list)
            color_idx += 1
            
        if use_escort:
            self.bode_curves["Escort"] = self.ui.bode_graph.plot(pen=pg.mkPen(color=colors[color_idx], width=1.5), name="Escort", symbol='t', symbolSize=5)
            self.plot_data["Escort"] = ([], [])
            color_idx += 1
            
        if use_rigol:
            for ch in active_osc_channels:
                name = f"Rigol CH{ch}"
                self.bode_curves[name] = self.ui.bode_graph.plot(pen=pg.mkPen(color=colors[color_idx % len(colors)], width=1.5), name=name, symbol='s', symbolSize=5)
                self.plot_data[name] = ([], [])
                color_idx += 1

        # Užblokuojame mygtuką ir nustatome progresą į 0
        self.ui.btn_start_bode.setEnabled(False)
        self.ui.bode_progress.setValue(0)
        
        # 6. GIJOS PALEIDIMAS
        self.worker = BodeSweepWorker(
            self.mgr, target_config, start_f, stop_f, 
            self.ui.bode_points.value(), self.ui.bode_amp.value(), self.ui.bode_gen_ch.currentIndex() + 1
        )
        
        # Susiejame gijos signalus su GUI funkcijomis
        self.worker.data_point.connect(self.on_data)
        self.worker.progress.connect(self.ui.bode_progress.setValue)
        self.worker.finished.connect(lambda: self.ui.btn_start_bode.setEnabled(True))
        self.worker.error.connect(self.on_bode_error) # Apsauga nuo nulūžimo!
        
        self.worker.start()

    def on_data(self, freq, results):
        """
        Apklausos grįžtamojo ryšio priėmėjas (Callback).
        Gauna atsakymą iš prietaisų ir atvaizduoja jį logaritminiame grafike.
        """
        # Saugome bazinį dažnį ataskaitų eksportui
        self.main.bode_freqs.append(freq)

        # Konvertuojame GUI Vpp į Vrms: Vrms = Vpp / (2 * sqrt(2))
        v_gui_rms = self.ui.bode_amp.value() / (2 * math.sqrt(2))
        
        # PyQtGraph 'setLogMode' metodas X ašiai reikalauja, 
        # kad paduodamos reikšmės jau būtų log10 formatu.
        log_f = math.log10(freq)
        
        
        # Suderinamumas su senesne PDF/CSV eksporto sistema (kur palaikoma tik viena linija)
        if results:
            first_val = list(results.values())[0]
            db_legacy = 20 * math.log10(max(first_val, 1e-6) / v_gui_rms)
            self.main.bode_y.append(db_legacy)
        
        # Iteruojame per visus grąžintus matuoklių rezultatus
        for source, val in results.items():
            if source in self.plot_data:
                # Decibelų skaičiavimas: Gain(dB) = 20 * log10(V_out / V_in)
                # max() funkcija apsaugo nuo "math domain error", jei įtampa nukrenta iki/žemiau nulio
                db = 20 * math.log10(max(val, 1e-6) / v_gui_rms)
                
                # Išsaugome X ir Y koordinates atitinkamo prietaiso sąraše
                self.plot_data[source][0].append(log_f)
                self.plot_data[source][1].append(db)
                
                # Perbraižome kreivę su nauju tašku
                self.bode_curves[source].setData(self.plot_data[source][0], self.plot_data[source][1])

    def stop_sweep(self):
        """Priverstinis gijos stabdymas paspaudus STOP mygtuką."""
        if self.worker: self.worker.is_running = False

    def on_bode_error(self, err_msg):
        """
        Klaidų apdorojimas (Exception handler).
        Užtikrina, kad esant SCPI ar serial prievado klaidai, sistema neužšaltų, 
        o informuotų vartotoją ir grąžintų valdymą.
        """
        self.ui.btn_start_bode.setEnabled(True)
        self.ui.bode_progress.setValue(0)
        self.main.log_msg(f"BODE KLAIDA: {err_msg}")
        QMessageBox.critical(self.main, "Bode Skenavimo Klaida", f"Matavimo ciklas nutrūko:\n\n{err_msg}")