import serial
import time

class TTi1604:
    # 7-segmentų dekodavimo žemėlapis pagal vadovo kodą
    SEGMENTS = {
        0b1111110: "0", 0b0110000: "1", 0b1101101: "2", 0b1111001: "3",
        0b0110011: "4", 0b1011011: "5", 0b1011111: "6", 0b1110000: "7",
        0b1111111: "8", 0b1110011: "9",
    }

    def __init__(self, port):
        self.port = port
        # Vadovo nustatyti parametrai: 9600 baud, 8 data bits, 1 stop bit, No parity, Timeout 2.5s
        self.ser = serial.Serial(self.port, 9600, timeout=2.5)
        
        # BŪTINA SĄLYGA: Maitinimo užtikrinimas per RS-232
        self.ser.setRTS(False)  # RTS = logic 1 (-V)
        self.ser.setDTR(True)   # DTR = logic 0 (+V)
        time.sleep(0.5)

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # Aktyvuojamas nuotolinis valdymas
        self.ser.write(b'u') 
        self.ser.flush()
        time.sleep(0.3)

    def _decode_digit(self, byte):
        b = byte >> 1
        dp = byte & 0x01
        ch = self.SEGMENTS.get(b & 0x7F, "?")
        return ch + ("." if dp else "")

    def _decode_function(self, byte):
        func = byte & 0b111
        func_map = {0b001: "mV", 0b010: "V", 0b011: "mA", 0b100: "A", 0b101: "Ohm"}
        return func, func_map.get(func, "?")

    def _read_frame(self):
        """Laukia 0x0D starto baito ir nuskaito 10 baitų kadrą."""
        while True:
            b = self.ser.read(1)
            if not b: 
                return None
            if b[0] == 0x0D:
                frame = self.ser.read(9)
                if len(frame) == 9:
                    return b + frame

    def _parse_frame(self, frame):
        """Dekoduoja 10 baitų masyvą į realią reikšmę."""
        func_bits, func_str = self._decode_function(frame[1])
        sign = "-" if frame[3] == 0x2D else ""
        val_str = sign + "".join(self._decode_digit(frame[i]) for i in range(4, 9))
        try:
            return func_bits, float(val_str), func_str
        except ValueError:
            return None, None, None

    def _read_stable_value(self, expected_func, retries=5):
        """Filtruoja šiukšles ir grąžina tik prašomo matavimo tipo reikšmę."""
        for _ in range(retries):
            frame = self._read_frame()
            if frame:
                f_bits, val, f_str = self._parse_frame(frame)
                if f_bits == expected_func and val is not None:
                    return val
        return None

    def get_voltage(self):
        """Išsiunčia komandą 'f' (Voltage) ir grąžina reikšmę."""
        self.ser.reset_input_buffer()
        self.ser.write(b'f')
        self.ser.flush()
        time.sleep(0.3) # Duodamas laikas prietaiso stabilizacijai
        return self._read_stable_value(0b010)

    def get_current(self):
        """Išsiunčia komandą 'd' (Current) ir grąžina reikšmę."""
        self.ser.reset_input_buffer()
        self.ser.write(b'd')
        self.ser.flush()
        time.sleep(0.3)
        return self._read_stable_value(0b100)

    def close(self):
        """Grąžina prietaisą į vietinį valdymą ir uždaro prievadą."""
        if self.ser and self.ser.is_open:
            self.ser.write(b'v') 
            self.ser.close()