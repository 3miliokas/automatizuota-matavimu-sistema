import serial
import time

class TTi1604:
    """
    Aparatūrinė tvarkyklė (Driver), skirta TTi 1604 stalinio multimetro valdymui per RS-232.
    Prietaisas nesiunčia atsakymų ASCII tekstu (kaip SCPI), o transliuoja tiesioginį LCD
    ekrano segmentų būsenos atvaizdą. Todėl tvarkyklė atlieka bitinio lygio dekodavimą.
    """
    
    # 7-segmentų LCD ekrano skaičių dekodavimo žemėlapis.
    # Kiekvienas bitas atitinka vieną fizinį LCD segmentą (a, b, c, d, e, f, g).
    SEGMENTS = {
        0b1111110: "0", 0b0110000: "1", 0b1101101: "2", 0b1111001: "3",
        0b0110011: "4", 0b1011011: "5", 0b1011111: "6", 0b1110000: "7",
        0b1111111: "8", 0b1110011: "9",
    }
    
    # ASCII baitai, kurie imituoja fizinių mygtukų paspaudimus prietaiso priekinėje panelėje.
    CMD_MAP = {
        'UP': b'a', 'DOWN': b'b', 'AUTO': b'c', 'A': b'd', 'mA': b'e', 
        'V': b'f', 'OPERATE': b'g', 'OHM': b'i', 'FREQ': b'j', 
        'SHIFT': b'k', 'AC': b'l', 'DC': b'm', 'mV': b'n',
        'DIODE': b'h', 'CONT': b'o', 'NULL': b'p', 'RESET': b'q'
    }

    def __init__(self, port, baudrate=9600, logger=None):
        self.logger = logger
        self.port = port
        
        # Inicijuojamas serial prievadas. 
        # TTi 1604 prietaisui privalomas RTS=False ir DTR=True, kad maitintų optiškai izoliuotą RS-232 kabelį.
        self.ser = serial.Serial(self.port, baudrate, timeout=1.0)
        self.ser.setRTS(False) 
        self.ser.setDTR(True)  
        time.sleep(0.5)
        
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # 'u' baitas yra herojinis pažadinimo (wake-up) signalas.
        # Prietaisas pradeda siųsti duomenis tik gavęs šią komandą.
        self.ser.write(b'u')  
        self.ser.flush()
        time.sleep(0.3)
        if self.logger: self.logger(f"TTi 1604 [{self.port}]: Ryšys inicializuotas.")

    def close(self):
        """Saugiai uždaro ryšio prievadą."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _decode_digit(self, byte):
        """
        Iškoduoja vieną LCD ekrano skaitmenį iš 8 bitų baito.
        Žemiausias bitas (LSB) rodo, ar dega dešimtainis taškas (Decimal Point).
        Likusieji 7 bitai parodo patį skaičių.
        """
        b = byte >> 1
        dp = byte & 0x01
        ch = self.SEGMENTS.get(b & 0x7F, "?")
        return ch + ("." if dp else "")

    def _decode_function(self, byte):
        """
        Iškoduoja matavimo režimą iš antrojo duomenų rėmo baito.
        Bitai 0-2 nurodo matavimo funkciją (V, A, Ohm), o 3-ias bitas rodo AC arba DC būseną.
        """
        func = byte & 0b111
        ac_dc = (byte >> 3) & 1
        func_map = {
            0b001: "mV", 0b010: "V", 0b011: "mA", 0b100: "A", 
            0b101: "OHM", 0b110: "CONT", 0b111: "Hz"
        }
        return func_map.get(func, ""), "AC" if ac_dc else "DC"

    def read_frame(self):
        """
        Sinchronizuoja ir nuskaito vieną pilną 10 baitų duomenų rėmą.
        TTi protokole rėmas visada prasideda baito reikšme 0x0D (Carriage Return).
        Įdėtas timeout apsisaugojimui nuo begalinio ciklo.
        """
        start_t = time.time()
        while time.time() - start_t < 1.5: # Apsauga nuo pakibimo
            b = self.ser.read(1)
            if not b: return None
            # Jei randame rėmo pradžią (0x0D), nuskaitome likusius 9 baitus
            if b[0] == 0x0D:
                rest = self.ser.read(9)
                if len(rest) == 9:
                    return b + rest
        return None

    def get_reading(self, timeout=3.0):
        """
        Nuskaito dabartinę prietaiso reikšmę.
        """
        if not self.ser or not self.ser.is_open: return None, "", ""
        
        # Svarbu: NESIŲSK self.ser.reset_input_buffer() ČIA, 
        # nes tai "nukerpa" rėmą, kurį prietaisas galbūt jau pradėjo siųsti.
        
        start = time.time()
        valid_count = 0
        last_val = None
        
        while time.time() - start < timeout:
            # Jei prietaisas užmiega (nustoja siųsti srautą)
            if self.ser.in_waiting == 0 and (time.time() - start) > 1.0 and valid_count == 0:
                try:
                    self.ser.write(b'u')
                    self.ser.flush()
                except: pass
                time.sleep(0.1)
                
            frame = self.read_frame()
            if not frame: continue

            # Iškoduojamas režimas ir vienetai
            unit, mode = self._decode_function(frame[1])
            minus = (frame[3] >> 1) & 1

            # Iškoduojama LCD skaičių seka
            chars = []
            for d in frame[4:9]:
                ch = self._decode_digit(d)
                if ch[0] != "?":
                    chars.append(ch)
            digits = "".join(chars)

            if not digits: continue
            
            # Jei prietaisas rodo "L" (Overload/Limit)
            if "L" in digits: 
                if self.logger: self.logger("TTi RX: OFL")
                return float('inf'), unit, mode

            try:
                # Konvertuojame tekstinį skaičių į float formatą
                val = float(digits)
                if minus: val = -val
                
                last_val = val
                valid_count += 1
                
                # Sėkmingo nuskaitymo patikra: laukiame 2 vienodų kadrų po relės perjungimo
                if valid_count >= 2:
                    if self.logger: self.logger(f"TTi RX: {val:.4f} {unit} {mode}")
                    return val, unit, mode
            except ValueError:
                pass
                
        if self.logger: self.logger("TTi RX: Klaida (nepavyko nuskaityti stabilaus rėmo)")
        return None, "", ""

    def send_command(self, cmd_key):
        """
        Siunčia vieną konfigūracinę komandą (simuliuoja mygtuko paspaudimą).
        Privaloma 0.3s pauzė, kad prietaiso vidinės mechaninės relės spėtų persijungti.
        """
        if not self.ser or not self.ser.is_open or cmd_key not in self.CMD_MAP: 
            return False
        if self.logger: self.logger(f"TTi TX: {cmd_key}")
        
        try:
            self.ser.write(self.CMD_MAP[cmd_key])
            self.ser.flush()
        except Exception as e:
            if self.logger: self.logger(f"TTi COM Prievado Klaida: {e}")
            # Užuot nulaužę programą, grąžiname False. 
            # Tai leis programai tęsti darbą ir pabandyti iš naujo.
            return False
            
        time.sleep(0.3) 
        return True

    def execute_macro(self, commands):
        """
        Išsiunčia seriją komandų (makrokomandą).
        Naudojama Bode Sweep ir Logger moduliuose, kai reikia perjungti prietaisą
        į specifinį režimą (pvz., komandų seka: "V", "AC", "AUTO").
        """
        if not self.ser or not self.ser.is_open: return False
        
        for cmd in commands:
            success = self.send_command(cmd)
            if not success: 
                return False # Nutraukiame makrokomandą, jei COM prievadas atmetė baitą
            time.sleep(0.2)
        return True