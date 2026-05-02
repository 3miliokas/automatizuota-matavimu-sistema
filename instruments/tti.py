import serial
import time

class TTi1604:
    SEGMENTS = {
        0b1111110: "0", 0b0110000: "1", 0b1101101: "2", 0b1111001: "3",
        0b0110011: "4", 0b1011011: "5", 0b1011111: "6", 0b1110000: "7",
        0b1111111: "8", 0b1110011: "9",
        0b0000000: "",   
        0b0000001: "-",  
        0b0001110: "L",  
    }
    
    CMD_MAP = {
        'UP': b'a', 'DOWN': b'b', 'AUTO': b'c', 'A': b'd', 'mA': b'e', 
        'V': b'f', 'OPERATE': b'g', 'OHM': b'i', 'FREQ': b'j', 
        'SHIFT': b'k', 'AC': b'l', 'DC': b'm', 'mV': b'n'
    }

    def __init__(self, port, baudrate=9600, logger=None):
        self.logger = logger
        self.port = port
        self.ser = serial.Serial(self.port, baudrate, timeout=2.5)
        self.ser.setRTS(False) 
        self.ser.setDTR(True)  
        time.sleep(0.5)
        
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(b'u') 
        self.ser.flush()
        time.sleep(0.3)
        if self.logger: self.logger(f"TTi 1604 [{self.port}]: Ryšys inicializuotas.")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _decode_digit(self, byte):
        b = byte >> 1
        dp = byte & 0x01
        ch = self.SEGMENTS.get(b & 0x7F, "?")
        return ch + ("." if dp else "")

    def send_command(self, cmd_key):
        if not self.ser or not self.ser.is_open or cmd_key not in self.CMD_MAP: 
            return False
        
        if self.logger: self.logger(f"TTi TX: {cmd_key}")
        self.ser.reset_input_buffer()
        self.ser.write(b'u')
        time.sleep(0.1)
        self.ser.write(self.CMD_MAP[cmd_key])
        self.ser.flush()
        time.sleep(0.3)
        return True

    def get_reading(self):
        if not self.ser or not self.ser.is_open: 
            return None, "", ""
            
        self.ser.reset_input_buffer()
        self.ser.write(b'u')
        time.sleep(0.1)
        
        history = []
        start_time = time.time()
        
        while time.time() - start_time < 4.0:
            if self.ser.in_waiting == 0:
                time.sleep(0.01)
                continue
                
            data = self.ser.read(1)
            if not data: continue
            
            history.append(data[0])
            if len(history) > 10:
                history.pop(0)
                
            if len(history) == 10 and history[0] == 0x0D and history[9] == 0x06:
                func_byte = history[1]
                ac_dc_flag = (func_byte >> 3) & 1
                func = func_byte & 0b111
                
                func_map = {0b001: "mV", 0b010: "V", 0b011: "mA", 0b100: "A", 0b101: "OHM", 0b111: "Hz"}
                unit = func_map.get(func, "")
                mode = "AC" if ac_dc_flag else "DC"

                d5 = self._decode_digit(history[4])
                d4 = self._decode_digit(history[5])
                d3 = self._decode_digit(history[6])
                d2 = self._decode_digit(history[7])
                d1 = self._decode_digit(history[8])

                if "?" not in (d1, d2, d3, d4, d5):
                    minus = "-" in (d5, d4, d3, d2, d1) or ((history[3] >> 1) & 1) == 1
                    digits = (d5 + d4 + d3 + d2 + d1).replace("..", ".").replace("-", "")
                    
                    if digits.startswith("."): digits = "0" + digits
                        
                    if "L" in digits: 
                        if self.logger: self.logger("TTi RX: OFL")
                        return float('inf'), unit, mode
                    
                    try:
                        val = float(digits)
                        if minus: val = -val
                        
                        if self.logger: self.logger(f"TTi RX: {val:.4f} {unit} {mode}")
                        self.ser.reset_input_buffer()
                        return val, unit, mode
                    except ValueError:
                        pass
        
        if self.logger: self.logger("TTi RX: Klaida (nepavyko gauti rėmo per 4 s.)")
        return None, "", ""