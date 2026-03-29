import serial
import time
import re

class Escort3136A:
    def __init__(self, port):
        self.port = port
        self.ser = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False
        )
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # Regex formatas skaičių su moksliniu formatu arba standartiniu atpažinimui
        self.number_pattern = re.compile(r'[-+]?\d*\.\d+E[-+]?\d+|[-+]?\d+\.\d*')

    def set_mode(self, mode_cmd):
        """Siunčia režimo keitimo komandą (S103 - Vdc, S145 - Adc)."""
        self.ser.write(mode_cmd.encode('ascii') + b"\r\n")
        time.sleep(0.5) # Duodamas laikas rėlei persijungti
        self.ser.reset_input_buffer()

    def read_value(self):
        """Siunčia skaitymo užklausą ir ieško skaitinės reikšmės."""
        self.ser.write(b"R1\r\n")
        time.sleep(0.3)
        
        for _ in range(5):
            line = self.ser.readline().decode(errors='ignore').strip()
            if line:
                match = self.number_pattern.search(line)
                if match:
                    return float(match.group())
        return None

    def get_voltage_dc(self):
        self.set_mode('S103')
        return self.read_value()

    def get_current_dc(self):
        self.set_mode('S145')
        return self.read_value()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()