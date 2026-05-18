import os
import re
from datetime import datetime
import pyvisa
import serial.tools.list_ports
import pyqtgraph as pg
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QApplication, QProgressDialog
from PyQt6.QtCore import QTimer, Qt

from gui.ui_layout import Ui_MainWindow
from gui.theme import STYLE_NORMAL, STYLE_ACTIVE, STYLE_SUCCESS, STYLE_DANGER
from core.instrument_manager import InstrumentManager
from core.exporters import export_curves_csv, export_bode_csv, generate_pdf_report

from controllers.gen_ctrl import GenController
from controllers.osc_ctrl import OscController
from controllers.tti_ctrl import TtiController
from controllers.escort_ctrl import EscortController
from controllers.bode_ctrl import BodeController
from controllers.log_ctrl import LogController


class MainWindow(QMainWindow):
    """
    Pagrindinė programos lango klasė.
    Atsakinga už grafinės sąsajos (GUI) inicializaciją, grafikų konfigūravimą,
    valdiklių (controllers) susiejimą su UI elementais bei bendrą aparatūros būsenos sinchronizaciją.
    """
    def __init__(self):
        super().__init__()
        
        # 1. UI ir pagrindinių valdiklių inicializacija
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)
        
        self.mgr = InstrumentManager(logger=self.log_msg)
        self.loading_count = 0
        self.loading_overlay = None

        # 2. Oscilogramos grafikų konfigūracija (CH1-CH4)
        self.curves = {}
        colors = ['#FFFF00', '#00FFFF', '#FF00FF', '#00FF00']
        for i in range(1, 5):
            self.curves[i] = self.ui.graph_widget.plot(pen=pg.mkPen(color=colors[i-1], width=1.5), name=f"CH{i}")
            self.curves[i].setVisible(False)
        
        # 3. Bode, Logger ir FFT grafikų masyvų inicializacija
        self.bode_freqs, self.bode_x, self.bode_y = [], [], []
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')
        
        self.log_x, self.log_y = [], []
        self.log_line = self.ui.log_graph.plot(self.log_x, self.log_y, pen='g')
        
        self.fft_x, self.fft_y = [], []
        self.fft_line = self.ui.fft_graph.plot(self.fft_x, self.fft_y, pen='m', fillLevel=0, brush=(156,39,176,50))

        # 4. Interaktyvių žymeklių (Crosshairs) priskyrimas grafikams
        self.crosshairs = []
        self.setup_crosshair(self.ui.graph_widget, "s", "V")
        self.setup_crosshair(self.ui.bode_graph, "Hz", "dB", is_log_x=True)
        self.setup_crosshair(self.ui.log_graph, "s", "V/A")
        self.setup_crosshair(self.ui.fft_graph, "Hz", "V")

        # 5. Modulių valdiklių (Controllers) instancijavimas
        self.gen_ctrl = GenController(self, self.ui, self.mgr)
        self.osc_ctrl = OscController(self, self.ui, self.mgr)
        self.tti_ctrl = TtiController(self, self.ui, self.mgr)
        self.escort_ctrl = EscortController(self, self.ui, self.mgr)
        self.bode_ctrl = BodeController(self, self.ui, self.mgr)
        self.log_ctrl = LogController(self, self.ui, self.mgr)

        # 6. Pagrindinių mygtukų signalų ir veiksmų (Slots) susiejimas
        self.ui.btn_scan.clicked.connect(self.scan_devices)
        self.ui.btn_generate_pdf.clicked.connect(self.generate_pdf)
        self.ui.btn_save_log.clicked.connect(self.save_system_log)
        self.ui.btn_export.clicked.connect(lambda: export_curves_csv(self.curves, QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")[0], self.log_msg))
        self.ui.btn_export_bode.clicked.connect(lambda: export_bode_csv(self.bode_freqs, self.bode_y, QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")[0], self.log_msg))
        self.ui.bode_device.currentIndexChanged.connect(self.toggle_bode_osc_ch)

        # 7. Fono sinchronizacijos laikmatis (Polling)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.poll_hardware)
        self.sync_timer.start(2000)

    def show_loading(self, text="Prašome palaukti..."):
        """Parodo blokuojantį krovimo langą, apsaugantį nuo naudotojo įvesčių siunčiant komandas."""
        if self.loading_overlay is None:
            self.loading_overlay = QProgressDialog(text, None, 0, 0, self)
            self.loading_overlay.setWindowTitle("Vykdoma...")
            self.loading_overlay.setWindowModality(Qt.WindowModality.WindowModal)
            self.loading_overlay.setMinimumDuration(0)
            self.loading_overlay.setCancelButton(None)
        else:
            self.loading_overlay.setLabelText(text)
        self.loading_count += 1
        self.loading_overlay.show()
        QApplication.processEvents()

    def hide_loading(self):
        """Paslepia krovimo langą, kai visos fono operacijos baigtos."""
        if self.loading_count > 0: 
            self.loading_count -= 1
        if self.loading_count == 0 and self.loading_overlay:
            self.loading_overlay.close()
            self.loading_overlay = None

    def update_toggle_button_style(self, btn, is_checked):
        """Atnaujina mygtuko stilių priklausomai nuo jo būsenos (Aktyvus / Neaktyvus)."""
        btn.setStyleSheet(STYLE_ACTIVE if is_checked else STYLE_NORMAL)

    def update_run_stop_btn(self, btn, is_running):
        """Specifinis stiliaus atnaujinimas oscilografo RUN/STOP mygtukui."""
        if is_running:
            btn.setStyleSheet(STYLE_SUCCESS)
            btn.setText("RUN (Veikia)")
        else:
            btn.setStyleSheet(STYLE_DANGER)
            btn.setText("STOP (Sustabdyta)")

    def setup_crosshair(self, plot_widget, unit_x, unit_y, is_log_x=False):
        """
        Sukonfigūruoja interaktyvius grafiko žymeklius (kryželį) ir matavimų vertes pelės pozicijoje.
        Įgyvendina pikselių koordinačių transformaciją į fizinius grafiko vienetus.
        """
        vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine))
        hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine))
        label = pg.TextItem(color='white', fill=pg.mkBrush(0, 0, 0, 200))
        label.setAnchor((1.1, 1.1))
        
        plot_widget.addItem(vLine, ignoreBounds=True)
        plot_widget.addItem(hLine, ignoreBounds=True)
        plot_widget.addItem(label, ignoreBounds=True)
        
        def mouse_moved(evt):
            pos = evt[0]
            if plot_widget.sceneBoundingRect().contains(pos):
                # Pikselių koordinačių transformacija į grafiko vertes
                mouse_point = plot_widget.plotItem.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                
                vLine.setPos(x)
                hLine.setPos(y)
                label.setPos(x, y)
                
                # Atsižvelgiama į logaritminę X ašį (Bode diagramai)
                disp_x = 10**x if is_log_x else x
                label.setText(f"X: {disp_x:.4g} {unit_x}\nY: {y:.4g} {unit_y}")

        # Optimizuotas signalų maršrutizavimas apribojant atnaujinimo dažnį (60 Hz)        
        proxy = pg.SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=mouse_moved)
        self.crosshairs.append((proxy, mouse_moved))

    def log_msg(self, text):
        """Įrašo pranešimą į sistemos žurnalą kartu su esamu laiku."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.log_console.append(f"[{timestamp}] {text}")
        # Automatinis slinkimas į apačią
        self.ui.log_console.verticalScrollBar().setValue(self.ui.log_console.verticalScrollBar().maximum())

    def closeEvent(self, event):
        """Saugus programos uždarymas: stabdomi laikmačiai ir uždaromos aparatūros sesijos."""
        self.sync_timer.stop()
        if hasattr(self.osc_ctrl, 'stream_timer'): 
            self.osc_ctrl.stream_timer.stop()
        self.mgr.close_all()
        event.accept()

    def scan_devices(self):
        """Inicijuoja VISA ir COM prievadų skenavimą."""
        self.sync_timer.stop()
        if hasattr(self.osc_ctrl, 'stream_timer'): 
            self.osc_ctrl.stream_timer.stop()
        self.show_loading("Ieškoma VISA ir COM prietaisų...")
        # Naudojamas QTimer.singleShot, kad spėtų atsinaujinti GUI (krovimo langas) prieš užblokuojant giją
        QTimer.singleShot(500, self._perform_scan_devices)

    def _perform_scan_devices(self):
        """Fizinis prietaisų skenavimas ir automatinis priskyrimas atitinkamiems moduliams."""
        old_gen = self.ui.combo_gen.currentData()
        old_osc = self.ui.combo_osc.currentData()
        old_tti = self.ui.combo_tti.currentData()
        old_esc = self.ui.combo_escort.currentData()

        self.mgr.close_all()
        
        # Išvalome senuosius sąrašus
        for cb in [self.ui.combo_gen, self.ui.combo_osc, self.ui.combo_tti, self.ui.combo_escort]:
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("-- Neprijungta --", "")
            
        try:
            # Skenuojame VISA įrenginius (Generatorių ir Oscilografą)
            rm = pyvisa.ResourceManager()
            for addr in rm.list_resources():
                try:
                    inst = rm.open_resource(addr)
                    idn = inst.query("*IDN?").strip()
                    inst.close()
                    name = idn.split(',')[1] if len(idn.split(',')) > 1 else idn
                    item_text = f"{name} [{addr}]"
                    self.ui.combo_gen.addItem(item_text, addr)
                    self.ui.combo_osc.addItem(item_text, addr)
                except: 
                    pass # Ignoruojame neatsakančius prievadus
                
            # Skenuojame COM prievadus (Multimetrams)
            for port in serial.tools.list_ports.comports():
                info = f"{port.device} - {port.description}"
                self.ui.combo_tti.addItem(info, port.device)
                self.ui.combo_escort.addItem(info, port.device)
                
            # --- Autoselekcijos logika (atstatomi seni arba randami nauji pagal pavadinimą) ---
            
            # Generatorius
            gen_idx = self.ui.combo_gen.findData(old_gen)
            if gen_idx > 0: 
                self.ui.combo_gen.setCurrentIndex(gen_idx)
            else:
                for i in range(self.ui.combo_gen.count()):
                    if "SDG" in self.ui.combo_gen.itemText(i).upper():
                        self.ui.combo_gen.setCurrentIndex(i)
                        break

            # Oscilografas
            osc_idx = self.ui.combo_osc.findData(old_osc)
            if osc_idx > 0: 
                self.ui.combo_osc.setCurrentIndex(osc_idx)
            else:
                for i in range(self.ui.combo_osc.count()):
                    if "DS1" in self.ui.combo_osc.itemText(i).upper() or "MSO" in self.ui.combo_osc.itemText(i).upper():
                        self.ui.combo_osc.setCurrentIndex(i)
                        break

            # Multimetrai
            if old_tti and self.ui.combo_tti.findData(old_tti) > 0: 
                self.ui.combo_tti.setCurrentIndex(self.ui.combo_tti.findData(old_tti))
            if old_esc and self.ui.combo_escort.findData(old_esc) > 0: 
                self.ui.combo_escort.setCurrentIndex(self.ui.combo_escort.findData(old_esc))

            # Prisijungiame prie parinktų įrenginių
            if self.ui.combo_gen.currentData(): self.mgr.connect_gen(self.ui.combo_gen.currentData())
            if self.ui.combo_osc.currentData(): self.mgr.connect_osc(self.ui.combo_osc.currentData())
            if self.ui.combo_tti.currentData(): self.mgr.connect_tti(self.ui.combo_tti.currentData())
            if self.ui.combo_escort.currentData(): self.mgr.connect_esc(self.ui.combo_escort.currentData())

            # Sinchronizuojame GUI būseną pagal realią aparatūros būseną
            self.gen_ctrl.sync_ui()
            self.osc_ctrl.sync_ui()
            self.tti_ctrl.refresh()
            self.escort_ctrl.refresh()
            
            self.log_msg("Fizinės įrangos skenavimas baigtas.")
        except Exception as e:
            self.log_msg(f"Klaida skenuojant prietaisus: {e}")
        finally:
            # Atblokuojame signalus ir atkuriame procesus
            for cb in [self.ui.combo_gen, self.ui.combo_osc, self.ui.combo_tti, self.ui.combo_escort]: 
                cb.blockSignals(False)
            self.hide_loading()
            self.sync_timer.start(2000)

    def poll_hardware(self):
        """
        Laikmačio funkcija, skirta periodiškai atnaujinti GUI parametrus pagal fizinės įrangos būseną.
        Vykdoma tik tada, kai nevyksta kritinės fono užduotys (Bode, Logger ar Live Stream).
        """
        if hasattr(self.osc_ctrl, 'stream_timer') and self.osc_ctrl.stream_timer.isActive(): return
        if self.bode_ctrl.worker and self.bode_ctrl.worker.isRunning(): return
        if self.log_ctrl.worker and self.log_ctrl.worker.isRunning(): return
        if self.loading_count > 0: return 
        
        self.gen_ctrl.sync_ui()
        self.osc_ctrl.sync_ui()

    def generate_pdf(self):
        """Inicijuoja PDF protokolo formavimą iš surinktų duomenų."""
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti PDF", "matavimu_protokolas.pdf", "PDF (*.pdf)")
        if not fn: return
        self.show_loading("Generuojamas PDF ataskaitos failas...")
        QTimer.singleShot(100, lambda: (generate_pdf_report(self.ui, (self.bode_x, self.bode_y), (self.log_x, self.log_y), fn, self.log_msg), self.hide_loading()))

    def save_system_log(self):
        """Išsaugo tekstinį sistemos žurnalą klaidų analizei."""
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Žurnalą", "zurnalas.log", "Log Files (*.log);;Text Files (*.txt)")
        if fn:
            try:
                with open(fn, 'w', encoding='utf-8') as f: 
                    f.write(self.ui.log_console.toPlainText())
                self.log_msg(f"Žurnalas išsaugotas: {fn}")
            except Exception as e:
                self.log_msg(f"Klaida: {e}")

    def toggle_bode_osc_ch(self, index):
        """Atvaizduoja/paslepia oscilografo kanalo pasirinkimą, priklausomai nuo to, ar matuoklis yra Rigol MSO."""
        is_rigol = (index == 0)
        self.ui.bode_osc_ch.setVisible(is_rigol)
        self.ui.lbl_bode_osc_ch.setVisible(is_rigol)