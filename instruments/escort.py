import serial
import re
import time

class Escort3136A:
    def __init__(self, port, logger=None):
        self.logger = logger
        self.port = port
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
        
        # Patobulintas Regex tikslesniam mokslinio ir standartinio skaičiaus atpažinimui
        self.number_pattern = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')

    def close(self):
        if self.ser.is_open:
            self.ser.close()

    def query(self, cmd):
        """Išsiunčia komandą ir efektyviai nuskaito atsakymą iki '>' simbolio be timeout uždelsimo."""
        if self.logger: self.logger(f"ESC TX: {cmd}")
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\r").encode('ascii'))
        self.ser.flush()
        
        # Escort atsakymą baigia simboliu '>', todėl skaitome tiksliai iki jo.
        raw_data = self.ser.read_until(b'>')
        text = raw_data.decode('ascii', errors='ignore')
        
        lines = [line.strip() for line in text.replace('\r', '\n').split('\n') if line.strip()]
        return lines

    def send_command(self, cmd):
        self.query(cmd)

    def read_value(self):
        val, _ = self.read_measurement()
        return val

    def read_measurement(self):
        val = None
        unit = ""
        
        # 1. Matavimo reikšmės nuskaitymas
        lines_r1 = self.query("R1")
        for line in lines_r1:
            if line == ">" or line == "R1": continue
            match = self.number_pattern.search(line)
            if match:
                try:
                    val = float(match.group())
                    break
                except ValueError:
                    pass
                    
        # 2. Matavimo režimo (vienetų) nuskaitymas
        if val is not None:
            lines_u1 = self.query("U1")
            for line in lines_u1:
                if line == ">" or line == "U1": continue
                if len(line) >= 1 and line[0].upper() in "0123456789AB":
                    m_char = line[0].upper()
                    mode_map = {
                        '0': "V DC", '1': "V AC", '2': "Ω", '3': "Ω",
                        '4': "A DC", '5': "A AC", '6': "V", '7': "Hz"
                    }
                    unit = mode_map.get(m_char, "")
                    break

        return val, unit