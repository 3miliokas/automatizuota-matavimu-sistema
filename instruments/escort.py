import serial
import re
import time

class Escort3136A:
    """
    Aparatūrinė tvarkyklė (Driver), skirta valdyti Escort 3136A stalinį multimetrą.
    Komunikacija vykdoma per RS-232 (arba USB-to-Serial virtualų COM) prievadą.
    """
    def __init__(self, port, logger=None):
        self.logger = logger
        self.port = port
        
        # Inicijuojamas nuoseklusis prievadas pagal gamintojo specifikacijas:
        # 9600 baud, 8 duomenų bitai, be pariteto, 1 stop bitas, be srauto valdymo.
        self.ser = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1.0,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False
        )
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # Patobulintas Regex (reguliariųjų išraiškų) šablonas, skirtas patikimai atpažinti 
        # tiek standartinius slankiojo kablelio skaičius, tiek mokslinį formatą (pvz., -1.23e-4).
        self.number_pattern = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')

    def close(self):
        """Saugiai uždaro nuosekliojo prievado ryšį."""
        if self.ser.is_open:
            self.ser.close()

    def query(self, cmd):
        """
        Išsiunčia komandą ir efektyviai nuskaito atsakymą.
        Optimizacija: Escort prietaisas kiekvieno atsakymo pabaigoje grąžina '>' simbolį.
        Naudojant 'read_until(b'>')', išvengiama laukimo iki timeout pabaigos,
        todėl ryšys tampa žymiai greitesnis.
        """
        if self.logger: self.logger(f"ESC TX: {cmd}")
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\r").encode('ascii'))
        self.ser.flush()
        
        # Skaitoma tiksliai iki užklausos pabaigos indikatoriaus
        raw_data = self.ser.read_until(b'>')
        text = raw_data.decode('ascii', errors='ignore')
        
        # Atsakymas išvalomas nuo tuščių eilučių ir grąžinimo (CR) simbolių
        lines = [line.strip() for line in text.replace('\r', '\n').split('\n') if line.strip()]
        return lines

    def send_command(self, cmd):
        """Išsiunčia komandą, bet ignoruoja atsakymą (naudojama režimų perjungimui)."""
        self.query(cmd)

    def read_value(self):
        """Pagalbinė funkcija, grąžinanti tik skaliarinę matavimo reikšmę (be vienetų)."""
        val, _ = self.read_measurement()
        return val

    def read_measurement(self):
        """
        Atlieka pilną prietaiso būsenos ir duomenų nuskaitymą dviem etapais:
        1. Nuskaito matavimo reikšmę.
        2. Nuskaito aktyvų matavimo režimą ir priskiria matavimo vienetus.
        """
        val = None
        unit = ""
        
        # --- 1. Matavimo reikšmės nuskaitymas (R1 komanda) ---
        lines_r1 = self.query("R1")
        for line in lines_r1:
            if line == ">" or line == "R1": continue
            # Taikomas Regex šablonas skaičiaus ištraukimui iš tekstinės eilutės
            match = self.number_pattern.search(line)
            if match:
                try:
                    val = float(match.group())
                    break
                except ValueError:
                    pass
                    
        # --- 2. Matavimo režimo ir vienetų nuskaitymas (U1 komanda) ---
        if val is not None:
            lines_u1 = self.query("U1")
            for line in lines_u1:
                if line == ">" or line == "U1": continue
                # Pirmasis simbolis nurodo aktyvų režimą pagal gamintojo protokolą
                if len(line) >= 1 and line[0].upper() in "0123456789AB":
                    m_char = line[0].upper()
                    mode_map = {
                        '0': "V DC", '1': "V AC", '2': "Ω", '3': "Ω",
                        '4': "A DC", '5': "A AC", '6': "V", '7': "Hz"
                    }
                    unit = mode_map.get(m_char, "")
                    break

        return val, unit