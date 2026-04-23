import serial
import time

class TTi1604:
    SEGMENTS = {
        0b1111110: "0", 0b0110000: "1", 0b1101101: "2", 0b1111001: "3",
        0b0110011: "4", 0b1011011: "5", 0b1011111: "6", 0b1110000: "7",
        0b1111111: "8", 0b1110011: "9",
    }
    
    CMD_MAP = {
        'UP': b'a', 'DOWN': b'b', 'AUTO': b'c', 'A': b'd', 'mA': b'e', 
        'V': b'f', 'OPERATE': b'g', 'OHM': b'i', 'FREQ': b'j', 
        'SHIFT': b'k', 'AC': b'l', 'DC': b'm', 'mV': b'n'
    }

    def __init__(self, port, baudrate=9600):
        self.port = port
        self.ser = serial.Serial(self.port, baudrate, timeout=2.5)
        self.ser.setRTS(False) 
        self.ser.setDTR(True)  
        time.sleep(0.5)

    def _decode_digit(self, byte):
        b = byte >> 1
        dp = byte & 0x01
        ch = self.SEGMENTS.get(b & 0x7F, "?")
        return ch + ("." if dp else "")

    def _decode_function_range(self, byte):
        func = byte & 0b111
        ac_dc = (byte >> 3) & 1
        func_map = {
            0b001: "mV", 0b010: "V", 0b011: "mA", 0b100: "A",
            0b101: "Ohm", 0b110: "Continuity", 0b111: "Diode"
        }
        unit = func_map.get(func, "Unknown")
        mode = "AC" if ac_dc else "DC"
        return unit, mode

    def _read_frame(self):
        while True:
            b = self.ser.read(1)
            if not b: return None
            if b[0] == 0x0D:
                rest = self.ser.read(9)
                if len(rest) == 9: return b + rest

    def _read_measurement(self):
        frame = self._read_frame()
        if not frame: return None
        
        unit, mode = self._decode_function_range(frame[1])
        minus = (frame[3] >> 1) & 1
        
        chars = []
        for d in frame[4:9]:
            ch = self._decode_digit(d)
            if ch[0] != "?":
                chars.append(ch)
        digits = "".join(chars)
        
        if not digits: return None
        try:
            val = float(digits)
            if minus: val = -val
            return val, unit, mode
        except ValueError:
            return None

    def send_command(self, cmd_key):
        if not self.ser.is_open or cmd_key not in self.CMD_MAP: 
            return False
        
        self.ser.reset_input_buffer()
        self.ser.write(b'u')
        time.sleep(0.1)
        self.ser.write(self.CMD_MAP[cmd_key])
        self.ser.flush()
        time.sleep(0.3)
        return True

    def get_reading(self):
        self.ser.reset_input_buffer()
        self.ser.write(b'u')
        time.sleep(0.1)

        start_time = time.time()
        valid_count = 0
        last_valid = None

        while time.time() - start_time < 3.0:
            m = self._read_measurement()
            if not m: continue
            
            val, unit, mode = m
            if isinstance(val, float):
                last_valid = (val, unit, mode)
                valid_count += 1
                if valid_count >= 2:
                    return last_valid
                    
        return None, "KLAIDA", ""

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b'v')
            self.ser.close()