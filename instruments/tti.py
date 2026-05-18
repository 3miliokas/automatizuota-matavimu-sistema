import serial
import time

class TTi1604:
    """
    Aparatūrinė tvarkyklė (Driver), skirta valdyti Thurlby Thandar Instruments (TTi) 1604 
    stalinį multimetrą. Šis prietaisas naudoja senos kartos, specifinį binarinį RS-232 protokolą,
    kurį ši klasė iškoduoja atgal į inžinerinius vienetus.
    """
    
    # 7 segmentų LED indikatoriaus bitų žemėlapis (Bitmask). 
    # Binariniai duomenys, gaunami iš prietaiso, atitinka fizinių LED segmentų būsenas.
    SEGMENTS = {
        0b1111110: "0", 0b0110000: "1", 0b1101101: "2", 0b1111001: "3",
        0b0110011: "4", 0b1011011: "5", 0b1011111: "6", 0b1110000: "7",
        0b1111111: "8", 0b1110011: "9",
        0b0000000: "",   
        0b0000001: "-",  
        0b0001110: "L",  # Naudojamas "OFL" (Overload) indikacijai
    }
    
    # TTi prietaiso klaviatūros imitavimo komandos
    CMD_MAP = {
        'UP': b'a', 'DOWN': b'b', 'AUTO': b'c', 'A': b'd', 'mA': b'e', 
        'V': b'f', 'OPERATE': b'g', 'OHM': b'i', 'FREQ': b'j', 
        'SHIFT': b'k', 'AC': b'l', 'DC': b'm', 'mV': b'n'
    }

    def __init__(self, port, baudrate=9600, logger=None):
        self.logger = logger
        self.port = port
        
        # Inicijuojamas ryšys (9600 baud, 8 bitai, be pariteto)
        self.ser = serial.Serial(self.port, baudrate, timeout=2.5)
        
        # Pagal TTi RS-232 specifikaciją, hardware flow control turi būti išjungtas,
        # bet DTR signalas reikalingas ryšiui palaikyti.
        self.ser.setRTS(False) 
        self.ser.setDTR(True)  
        time.sleep(0.5)
        
        # Išvalomi ryšio buferiai ir prietaisui nusiunčiamas 'u' baitas 
        # (užklausos signalas rėmo sinchronizacijai).
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(b'u') 
        self.ser.flush()
        time.sleep(0.3)
        
        if self.logger: self.logger(f"TTi 1604 [{self.port}]: Ryšys inicializuotas.")

    def close(self):
        """Saugiai uždaro COM prievadą."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _decode_digit(self, byte):
        """
        Iškoduoja vieną binarinio rėmo baitą į atitinkamą ASCII simbolį.
        Prietaiso protokolas: jauniausias bitas (LSB) indikuoja dešimtainį kablelį (DP),
        kiti 7 bitai indikuoja LED segmentus.
        """
        b = byte >> 1
        dp = byte & 0x01
        ch = self.SEGMENTS.get(b & 0x7F, "?")
        return ch + ("." if dp else "")

    def send_command(self, cmd_key):
        """Išsiunčia vieno mygtuko paspaudimą imituojančią komandą iš CMD_MAP žodyno."""
        if not self.ser or not self.ser.is_open or cmd_key not in self.CMD_MAP: 
            return False
        
        if self.logger: self.logger(f"TTi TX: {cmd_key}")
        self.ser.reset_input_buffer()
        
        # Pagal protokolą, pirma reikia sužadinti prietaisą su 'u', po to siųsti komandą
        self.ser.write(b'u')
        time.sleep(0.1)
        self.ser.write(self.CMD_MAP[cmd_key])
        self.ser.flush()
        time.sleep(0.3)
        return True

    def get_reading(self):
        """
        Gaudymo ciklas, kuris laukia ir dekoduoja 10 baitų ilgio duomenų rėmą (Frame).
        Grąžina iškoduotą reikšmę (float), matavimo vienetą ir rėžimą (AC/DC).
        """
        if not self.ser or not self.ser.is_open: 
            return None, "", ""
            
        self.ser.reset_input_buffer()
        self.ser.write(b'u')
        time.sleep(0.1)
        
        history = []
        start_time = time.time()
        
        # Ciklas bando pagauti pilną, nesugadintą 10 baitų rėmą per 4 sekundes
        while time.time() - start_time < 4.0:
            if self.ser.in_waiting == 0:
                time.sleep(0.01)
                continue
                
            data = self.ser.read(1)
            if not data: continue
            
            # Formuojamas binarinis buferis
            history.append(data[0])
            if len(history) > 10:
                history.pop(0)

            # Rėmo sinchronizacijos patikrinimas: pradžios (0x0D) ir pabaigos (0x06) baitų identifikavimas   
            if len(history) == 10 and history[0] == 0x0D and history[9] == 0x06:
                
                # 2-as rėmo baitas saugo informaciją apie matavimo režimą ir tipą
                func_byte = history[1]
                ac_dc_flag = (func_byte >> 3) & 1
                func = func_byte & 0b111
                
                func_map = {0b001: "mV", 0b010: "V", 0b011: "mA", 0b100: "A", 0b101: "OHM", 0b111: "Hz"}
                unit = func_map.get(func, "")
                mode = "AC" if ac_dc_flag else "DC"

                # 5–9 rėmo baitai saugo išmatuoto parametro LED indikatorių reikšmes
                d5 = self._decode_digit(history[4])
                d4 = self._decode_digit(history[5])
                d3 = self._decode_digit(history[6])
                d2 = self._decode_digit(history[7])
                d1 = self._decode_digit(history[8])

                # Jei visi segmentai buvo sėkmingai atpažinti žodyne
                if "?" not in (d1, d2, d3, d4, d5):
                    # Nustatomas minuso ženklas (jei atskiras segmentas rodo minusą arba 4-o baito indikatorius teigiamas)
                    minus = "-" in (d5, d4, d3, d2, d1) or ((history[3] >> 1) & 1) == 1
                    
                    # Suformuojama skaičiaus tekstinė eilutė (String) pašalinant klaidingus simbolius
                    digits = (d5 + d4 + d3 + d2 + d1).replace("..", ".").replace("-", "")
                    
                    if digits.startswith("."): digits = "0" + digits
                        
                    # Jei ekrane dega 'L', tai reiškia Overload (viršytas matavimo diapazonas)
                    if "L" in digits: 
                        if self.logger: self.logger("TTi RX: OFL")
                        return float('inf'), unit, mode
                    
                    try:
                        # Tekstas konvertuojamas į bazinį slankiojo kablelio inžinerinį skaičių
                        val = float(digits)
                        if minus: val = -val
                        
                        if self.logger: self.logger(f"TTi RX: {val:.4f} {unit} {mode}")
                        self.ser.reset_input_buffer()
                        return val, unit, mode
                    except ValueError:
                        pass
        
        if self.logger: self.logger("TTi RX: Klaida (nepavyko gauti rėmo per 4 s.)")
        return None, "", ""