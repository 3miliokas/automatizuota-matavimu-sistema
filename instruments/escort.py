import serial
import re
import time

class Escort3136A:
    """
    Aparatūrinė tvarkyklė (Driver), skirta valdyti Escort 3136A stalinį multimetrą.
    Protokolas paremtas mm3136A.sci specifikacija.
    """
    def __init__(self, port, logger=None):
        self.logger = logger
        self.port = port
        
        self.ser = serial.Serial(
            port=self.port, baudrate=9600, bytesize=8,
            parity='N', stopbits=1, timeout=0.5, # Sumažintas bazinis timeout, nes skaitysime dinamiškai
            rtscts=False, dsrdtr=False, xonxoff=False
        )
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # Pažadinimas ir buferio išvalymas (prietaisui reikia \r\n)
        self.ser.write(b"\r\n")
        time.sleep(0.1)
        self.ser.read_all()
        
        # Šablonas skaičiaus ištraukimui (įskaitant mokslinį formatą)
        self.number_pattern = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')
        if self.logger: self.logger(f"Escort 3136A [{self.port}]: Ryšys inicializuotas.")

    def close(self):
        if self.ser and self.ser.is_open:
            # GTL (Go To Local) atiduoda valdymą prietaiso fiziniams mygtukams
            self.ser.write(b"GTL\r\n") 
            time.sleep(0.1)
            self.ser.close()

    def query(self, cmd):
        """Išsiunčia komandą ir dinamiškai nuskaito atsakymą."""
        if not self.ser or not self.ser.is_open: return []
        if self.logger: self.logger(f"ESC TX: {cmd}")
        
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\r\n").encode('ascii'))
        self.ser.flush()
        
        # Dinaminis skaitymas (neblokuojantis ir saugus)
        raw_data = b""
        start_time = time.time()
        while time.time() - start_time < 1.0: # Maksimalus 1s timeout
            if self.ser.in_waiting:
                time.sleep(0.05) # Leidžiame prietaisui užbaigti siųsti eilutę
                raw_data += self.ser.read_all()
                # Escort atsakymai baigiasi nauja eilute arba '>' indikatoriumi
                if b'\n' in raw_data or b'>' in raw_data:
                    break
            time.sleep(0.01)
            
        text = raw_data.decode('ascii', errors='ignore')
        lines = [line.strip() for line in text.replace('\r', '\n').split('\n') if line.strip()]
        return lines

    def send_command(self, cmd):
        """Siunčia konfigūracinę komandą (pvz., režimo keitimą)."""
        self.query(cmd)

    def read_value(self):
        """Grąžina tik skaitinę reikšmę (naudojama Logger foninėje gijoje)."""
        val, _ = self.read_measurement()
        return val

    def read_measurement(self):
        """Atlieka pilną prietaiso būsenos ir duomenų nuskaitymą."""
        val = None
        unit = ""
        
        # 1. Matavimo reikšmės nuskaitymas (R1)
        lines_r1 = self.query("R1")
        if lines_r1:
            match = self.number_pattern.search(lines_r1[0])
            if match:
                try:
                    val = float(match.group())
                except ValueError:
                    pass
                    
        # 2. Režimo iškodavimas per R0 komandą
        if val is not None:
            lines_r0 = self.query("R0")
            # Apsauga nuo trumpo (nepilno) atsakymo
            if lines_r0 and len(lines_r0[0]) >= 8:
                f_char = lines_r0[0][7].upper() # 8-tas simbolis nurodo režimą pagal Scilab kodą
                
                # Režimų atvaizdavimas pagal Scilab / Escort 3136A protokolą
                mode_map = {
                    '0': "V DC", '1': "V AC", '8': "V AC+DC",
                    '4': "A DC", '5': "A AC", '9': "A AC+DC",
                    '2': "Ω", 'A': "Continuity", '6': "Diode",
                    '7': "Hz", 'B': "dBm"
                }
                unit = mode_map.get(f_char, "")

        if self.logger and val is not None: 
            self.logger(f"ESC RX: {val} {unit}")
            
        return val, unit