import os
from datetime import datetime
import pyvisa
import serial.tools.list_ports
import pyqtgraph as pg
from PyQt6.QtWidgets import (QMainWindow, QFileDialog, QApplication, QProgressDialog, 
                             QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel, QLineEdit)
from PyQt6.QtCore import QTimer, Qt

# Importuojamas grafinės vartotojo sąsajos (UI) karkasas, sugeneruotas iš ui_layout.py
from gui.ui_layout import Ui_MainWindow
from gui.theme import STYLE_NORMAL, STYLE_ACTIVE, STYLE_SUCCESS, STYLE_DANGER
from core.instrument_manager import InstrumentManager
from core.exporters import export_curves_csv, export_bode_csv, generate_pdf_report

# Valdiklių (Controllers) importavimas
from controllers.gen_ctrl import GenController
from controllers.osc_ctrl import OscController
from controllers.tti_ctrl import TtiController
from controllers.escort_ctrl import EscortController
from controllers.bode_ctrl import BodeController
from controllers.log_ctrl import LogController

class PDFExportDialog(QDialog):
    """
    Iššokantis (Modal) langas, kuris pasirodo vartotojui paspaudus "Generuoti PDF Ataskaitą".
    Leidžia įvesti eksperimento pastabas ir pasirinkti, kuriuos modulius (grafikus, lenteles)
    įtraukti į galutinį sugeneruotą PDF failą.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Ataskaitos Nustatymai")
        self.setModal(True)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Eksperimento pastabos / Pavadinimas (bus matoma PDF):"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Pvz.: RC filtras, C=470nF, R=1.1kOhm")
        self.layout.addWidget(self.notes_input)
        
        self.cb_gen = QCheckBox("1. Generatoriaus nustatymai (Visi parametrai)"); self.cb_gen.setChecked(True)
        self.layout.addWidget(self.cb_gen)
        self.cb_multi = QCheckBox("2. Multimetrų rodmenys"); self.cb_multi.setChecked(True)
        self.layout.addWidget(self.cb_multi)
        self.cb_osc_tab = QCheckBox("3. Oscilografo parametrų lentelė"); self.cb_osc_tab.setChecked(True)
        self.layout.addWidget(self.cb_osc_tab)
        self.cb_osc_graph = QCheckBox("4. Oscilogramos grafikas"); self.cb_osc_graph.setChecked(True)
        self.layout.addWidget(self.cb_osc_graph)
        self.cb_bode = QCheckBox("5. Bode diagrama (su nustatymais)"); self.cb_bode.setChecked(True)
        self.layout.addWidget(self.cb_bode)
        self.cb_log = QCheckBox("6. Logger diagrama (su nustatymais)"); self.cb_log.setChecked(True)
        self.layout.addWidget(self.cb_log)
        self.cb_fft = QCheckBox("7. FFT grafikas"); self.cb_fft.setChecked(True)
        self.layout.addWidget(self.cb_fft)
        
        # OK / Cancel mygtukų blokas
        self.btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        self.layout.addWidget(self.btns)

    def get_options(self):
        """Grąžina žodyną (dictionary) su vartotojo pasirinktomis ataskaitos opcijomis."""
        return {
            "notes": self.notes_input.text().strip(),
            "gen": self.cb_gen.isChecked(), "multi": self.cb_multi.isChecked(),
            "osc_table": self.cb_osc_tab.isChecked(), "osc_graph": self.cb_osc_graph.isChecked(),
            "bode": self.cb_bode.isChecked(), "log": self.cb_log.isChecked(), "fft": self.cb_fft.isChecked()
        }


class MainWindow(QMainWindow):
    """
    Pagrindinis programos langas (Main Window).
    Ši klasė apjungia grafinę sąsają (UI), prietaisų valdytoją (InstrumentManager)
    ir visus atskirus modulių valdiklius (Controllers). Ji taip pat tvarko globalius
    grafikų kintamuosius ir atlieka aparatūros skenavimą.
    """
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)
        
        # Sukuriamas sisteminis prietaisų valdytojas
        self.mgr = InstrumentManager(logger=self.log_msg)
        
        # Kintamieji, skirti valdyti "Konfigūruojama..." krovimo lentelę.
        # loading_count naudojamas todėl, kad gali būti keli vienalaikiai procesai.
        self.loading_count = 0
        self.loading_overlay = None

        # --- GRAFIKŲ DUOMENŲ STRUKTŪROS ---
        
        # 1. Oscilografo (Live Stream) kreivių žodynas
        self.curves = {}
        colors = ['#FFFF00', '#00FFFF', '#FF00FF', '#00FF00'] # Geltona, Žydra, Rožinė, Žalia
        for i in range(1, 5):
            self.curves[i] = self.ui.graph_widget.plot(pen=pg.mkPen(color=colors[i-1], width=1.5), name=f"CH{i}")
            self.curves[i].setVisible(False)
        
        # 2. Bode diagramos, Loggerio ir FFT atvaizdavimo linijos
        self.bode_freqs, self.bode_x, self.bode_y = [], [], []
        self.bode_line = self.ui.bode_graph.plot(self.bode_x, self.bode_y, pen='c', symbol='o')
        self.log_x, self.log_y = [], []
        self.log_line = self.ui.log_graph.plot(self.log_x, self.log_y, pen='g')
        self.fft_x, self.fft_y = [], []
        self.fft_line = self.ui.fft_graph.plot(self.fft_x, self.fft_y, pen='m', fillLevel=0, brush=(156,39,176,50))

        # --- Dinaminių pelės žymeklių (Crosshairs) nustatymas grafikams ---
        self.crosshairs = []
        self.setup_crosshair(self.ui.graph_widget, "s", "V")
        self.setup_crosshair(self.ui.bode_graph, "Hz", "dB", is_log_x=True)
        self.setup_crosshair(self.ui.log_graph, "s", "V/A")
        self.setup_crosshair(self.ui.fft_graph, "Hz", "V")

        # --- Modulių (Controllers) Inicializacija ---
        self.gen_ctrl = GenController(self, self.ui, self.mgr)
        self.osc_ctrl = OscController(self, self.ui, self.mgr)
        self.tti_ctrl = TtiController(self, self.ui, self.mgr)
        self.escort_ctrl = EscortController(self, self.ui, self.mgr)
        self.bode_ctrl = BodeController(self, self.ui, self.mgr)
        self.log_ctrl = LogController(self, self.ui, self.mgr)

        # Globalių mygtukų susiejimas
        self.ui.btn_scan.clicked.connect(self.scan_devices)
        self.ui.btn_generate_pdf.clicked.connect(self.generate_pdf)
        self.ui.btn_save_log.clicked.connect(self.save_system_log)
        
        # Funkcijos, eksportuojančios grafikus į CSV
        self.ui.btn_export.clicked.connect(lambda: export_curves_csv(self.curves, QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")[0], self.log_msg))
        self.ui.btn_export_bode.clicked.connect(lambda: export_bode_csv(self.bode_freqs, self.bode_ctrl.plot_data, QFileDialog.getSaveFileName(self, "Išsaugoti", "", "CSV (*.csv)")[0], self.log_msg))

        # Dinaminis UI elementų (kanalų pasirinkimo) slėpimas Bode ir Logger languose
        self.ui.cb_bode_rigol.stateChanged.connect(self.toggle_bode_osc_ch)
        self.toggle_bode_osc_ch()
        self.ui.log_device.currentIndexChanged.connect(self.toggle_log_osc_ch)
        self.toggle_log_osc_ch()

        # Sisteminis taimeris. Dabar naudojamas tik skenavimo procesui palaikyti. 
        # (Agresyvus parametrų perrašymas (polling) buvo išjungtas dėl UI konfliktų).
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.poll_hardware)
        self.sync_timer.start(2000)

    def toggle_bode_osc_ch(self):
        """Atvaizduoja/paslepia oscilografo kanalų pasirinkimą Bode lange pagal tai, ar pažymėtas Rigol MSO."""
        is_checked = self.ui.cb_bode_rigol.isChecked()
        self.ui.lbl_bode_osc_ch.setVisible(is_checked)
        self.ui.w_bode_chs.setVisible(is_checked)

    def toggle_log_osc_ch(self):
        """Slepia/rodo kanalų pasirinkimą Logger lange, priklausomai nuo pasirinkto prietaiso."""
        is_rigol = (self.ui.log_device.currentIndex() == 0)
        self.ui.lbl_log_osc_ch.setVisible(is_rigol)
        self.ui.log_osc_ch.setVisible(is_rigol)

    def show_loading(self, text="Prašome palaukti..."):
        """
        Iškviečia modalinį krovimo langą, kuris blokuoja GUI, kol prietaisas konfigūruojamas fone.
        Taip pat įrašo veiksmą į Sistemos Žurnalą (Log Console).
        """
        self.log_msg(f"Procesas: {text}") # Žurnalo fiksavimas
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
        """Uždaro krovimo langą, jei visi fono procesai baigėsi."""
        if self.loading_count > 0: 
            self.loading_count -= 1
        if self.loading_count == 0 and self.loading_overlay:
            self.loading_overlay.close()
            self.loading_overlay = None

    def update_toggle_button_style(self, btn, is_checked):
        """Pritaikomas stilius mygtukams (pvz., CH1 ON/OFF), kad jie vizualiai keistų spalvą."""
        btn.setStyleSheet(STYLE_ACTIVE if is_checked else STYLE_NORMAL)

    def update_run_stop_btn(self, btn, is_running):
        """Keičia Rigol RUN/STOP mygtuko vizualizaciją (Žalia/Raudona)."""
        if is_running:
            btn.setStyleSheet(STYLE_SUCCESS)
            btn.setText("RUN (Veikia)")
        else:
            btn.setStyleSheet(STYLE_DANGER)
            btn.setText("STOP (Sustabdyta)")

    def setup_crosshair(self, plot_widget, unit_x, unit_y, is_log_x=False):
        """
        Prideda dinamines X/Y ašių koordinačių linijas (Crosshairs) ir teksto laukelį (Label),
        kuris seka pelės žymeklį virš grafiko (PyQtGraph).
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
                mouse_point = plot_widget.plotItem.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                vLine.setPos(x); hLine.setPos(y); label.setPos(x, y)
                # Jei grafikas logaritminis (kaip Bode), tekstas konvertuojamas atgal į tikrus vienetus
                disp_x = 10**x if is_log_x else x
                label.setText(f"X: {disp_x:.4g} {unit_x}\nY: {y:.4g} {unit_y}")

        proxy = pg.SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=mouse_moved)
        self.crosshairs.append((proxy, mouse_moved))

    def log_msg(self, text):
        """Prideda pranešimą į GUI Sistemos Žurnalą su laiko žyma."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.log_console.append(f"[{timestamp}] {text}")
        # Automatiškai nuslenka žurnalą į patį galą
        self.ui.log_console.verticalScrollBar().setValue(self.ui.log_console.verticalScrollBar().maximum())

    def closeEvent(self, event):
        """Programos uždarymo logika: stabdomi laikmačiai ir saugiai atjungiami prietaisai."""
        self.sync_timer.stop()
        if hasattr(self.osc_ctrl, 'stream_timer'): self.osc_ctrl.stream_timer.stop()
        self.mgr.close_all()
        event.accept()

    def scan_devices(self):
        """Inicijuoja VISA / COM portų skenavimą ieškant aparatūros."""
        self.sync_timer.stop()
        if hasattr(self.osc_ctrl, 'stream_timer'): self.osc_ctrl.stream_timer.stop()
        self.show_loading("Ieškoma VISA ir COM prietaisų...")
        # Laukimas leidžia krovimo langui pasirodyti prieš užblokuojant giją (skenavimas užtrunka)
        QTimer.singleShot(500, self._perform_scan_devices)

    def _perform_scan_devices(self):
        """Fiziškai ieško prietaisų ir priskiria juos į ComboBox sąrašus."""
        old_gen = self.ui.combo_gen.currentData()
        old_osc = self.ui.combo_osc.currentData()
        old_tti = self.ui.combo_tti.currentData()
        old_esc = self.ui.combo_escort.currentData()

        self.mgr.close_all()
        for cb in [self.ui.combo_gen, self.ui.combo_osc, self.ui.combo_tti, self.ui.combo_escort]:
            cb.blockSignals(True); cb.clear(); cb.addItem("-- Neprijungta --", "")
            
        try:
            # 1. Ieškoma VISA prietaisų (USB-TMC)
            rm = pyvisa.ResourceManager()
            for addr in rm.list_resources():
                try:
                    inst = rm.open_resource(addr)
                    idn = inst.query("*IDN?").strip()
                    inst.close()
                    # Sukuriamas gražesnis pavadinimas
                    name = idn.split(',')[1] if len(idn.split(',')) > 1 else idn
                    item_text = f"{name} [{addr}]"
                    self.ui.combo_gen.addItem(item_text, addr)
                    self.ui.combo_osc.addItem(item_text, addr)
                except: pass
                
            # 2. Ieškoma virtualių / fizinių COM prievadų (RS-232)
            for port in serial.tools.list_ports.comports():
                info = f"{port.device} - {port.description}"
                self.ui.combo_tti.addItem(info, port.device)
                self.ui.combo_escort.addItem(info, port.device)
                
            # 3. Mėginama atkurti ankstesnį arba automatiškai parinkti tinkamą prietaisą
            gen_idx = self.ui.combo_gen.findData(old_gen)
            if gen_idx > 0: self.ui.combo_gen.setCurrentIndex(gen_idx)
            else:
                for i in range(self.ui.combo_gen.count()):
                    if "SDG" in self.ui.combo_gen.itemText(i).upper():
                        self.ui.combo_gen.setCurrentIndex(i); break

            osc_idx = self.ui.combo_osc.findData(old_osc)
            if osc_idx > 0: self.ui.combo_osc.setCurrentIndex(osc_idx)
            else:
                for i in range(self.ui.combo_osc.count()):
                    if "DS1" in self.ui.combo_osc.itemText(i).upper() or "MSO" in self.ui.combo_osc.itemText(i).upper():
                        self.ui.combo_osc.setCurrentIndex(i); break

            if old_tti and self.ui.combo_tti.findData(old_tti) > 0: 
                self.ui.combo_tti.setCurrentIndex(self.ui.combo_tti.findData(old_tti))
            if old_esc and self.ui.combo_escort.findData(old_esc) > 0: 
                self.ui.combo_escort.setCurrentIndex(self.ui.combo_escort.findData(old_esc))

            # 4. Automatinis prietaisų prijungimas, jei jie rasti
            if self.ui.combo_gen.currentData(): self.mgr.connect_gen(self.ui.combo_gen.currentData())
            if self.ui.combo_osc.currentData(): self.mgr.connect_osc(self.ui.combo_osc.currentData())
            if self.ui.combo_tti.currentData(): self.mgr.connect_tti(self.ui.combo_tti.currentData())
            if self.ui.combo_escort.currentData(): self.mgr.connect_esc(self.ui.combo_escort.currentData())

            self.log_msg("Fizinės įrangos skenavimas baigtas.")
        except Exception as e:
            self.log_msg(f"Klaida skenuojant prietaisus: {e}")
        finally:
            for cb in [self.ui.combo_gen, self.ui.combo_osc, self.ui.combo_tti, self.ui.combo_escort]: cb.blockSignals(False)
            self.hide_loading()
            self.sync_timer.start(2000)

    def poll_hardware(self):
        """ 
        Agresyvus fono parametrų atnaujinimas (polling) yra išjungtas,
        kad nesukeltų konfliktų su vartotojo įvestimi. 
        Atnaujinimas vykdomas tik paspaudus mygtukus (event-driven).
        """
        pass

    def generate_pdf(self):
        """Inicijuoja PDF Ataskaitos generavimo procesą."""
        dialog = PDFExportDialog(self)
        if dialog.exec():
            options = dialog.get_options()
            fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti PDF", "matavimu_protokolas.pdf", "PDF (*.pdf)")
            if not fn: return
            self.show_loading("Generuojamas PDF ataskaitos failas...")
            QTimer.singleShot(100, lambda: (
                generate_pdf_report(self.ui, (self.bode_x, self.bode_y), (self.log_x, self.log_y), options, fn, self.log_msg, self.mgr.osc),
                self.hide_loading()
            ))

    def save_system_log(self):
        """Išsaugo visą ekrane matomą žurnalo tekstą į tekstinį / .log failą."""
        fn, _ = QFileDialog.getSaveFileName(self, "Išsaugoti Žurnalą", "zurnalas.log", "Log Files (*.log);;Text Files (*.txt)")
        if fn:
            try:
                with open(fn, 'w', encoding='utf-8') as f: f.write(self.ui.log_console.toPlainText())
                self.log_msg(f"Žurnalas išsaugotas: {fn}")
            except Exception as e:
                self.log_msg(f"Klaida: {e}")