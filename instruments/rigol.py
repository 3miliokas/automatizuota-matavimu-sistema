import numpy as np

class RigolMSO:
    def __init__(self, resource_manager_addr, logger=None):
        self.logger = logger
        import pyvisa
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        self.inst.timeout = 5000

    def close(self):
        try:
            self.inst.close()
            self.rm.close()
        except: pass

    def write(self, cmd):
        if self.logger: self.logger(f"MSO TX: {cmd}")
        self.inst.write(cmd)

    def query(self, cmd):
        if self.logger: self.logger(f"MSO TX: {cmd}")
        resp = self.inst.query(cmd).strip()
        if "WAV:DATA?" not in cmd and "WAV:PRE?" not in cmd and "DISP:DATA?" not in cmd:
            if self.logger: self.logger(f"MSO RX: {resp}")
        return resp

    def set_channel_display(self, state, channel=1):
        s = "ON" if state else "OFF"
        self.write(f":CHANnel{channel}:DISPlay {s}")

    def get_channel_state(self, channel=1):
        try:
            resp = self.query(f":CHANnel{channel}:DISPlay?")
            return "1" in resp or "ON" in resp.upper()
        except: return False

    def get_run_state(self):
        try:
            resp = self.query(":TRIGger:STATus?")
            return "STOP" not in resp.upper()
        except: return False

    def auto_scale(self): 
        self.write(":AUToscale")
        
    def run(self): 
        self.write(":RUN")
        
    def stop(self): 
        self.write(":STOP")

    def get_measure(self, type, channel=1):
        old_timeout = self.inst.timeout
        self.inst.timeout = 500 
        try:
            val = float(self.query(f":MEASure:ITEM? {type},CHANnel{channel}"))
            self.inst.timeout = old_timeout
            return val
        except:
            self.inst.timeout = old_timeout
            return None

    def get_waveform_data(self, channel=1):
        self.write(f":WAV:SOUR CHANnel{channel}")
        self.write(":WAV:MODE NORM")
        self.write(":WAV:FORM BYTE")
        try:
            pre = self.query(":WAV:PRE?").split(',')
            if len(pre) < 10: return [], []
            x_inc, x_orig, x_ref = float(pre[4]), float(pre[5]), float(pre[6])
            y_inc, y_orig, y_ref = float(pre[7]), float(pre[8]), float(pre[9])
            
            if self.logger: self.logger("MSO TX: :WAV:DATA? (Binary Transfer)")
            raw = self.inst.query_binary_values(":WAV:DATA?", datatype='B', container=np.array, header_fmt='ieee')
            v = (raw - y_orig - y_ref) * y_inc
            t = np.arange(len(v)) * x_inc + x_orig
            return t, v
        except Exception as e:
            if self.logger: self.logger(f"MSO WAV Error: {e}")
            return [], []

    def get_screenshot(self):
        try:
            if self.logger: self.logger("MSO TX: :DISP:DATA? ON,OFF,PNG (Binary Transfer)")
            raw = self.inst.query_binary_values(":DISP:DATA? ON,OFF,PNG", datatype='B', container=bytes, header_fmt='ieee')
            return raw
        except Exception as e:
            if self.logger: self.logger(f"MSO Screenshot Error: {e}")
            return b""