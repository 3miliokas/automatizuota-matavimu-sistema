import numpy as np

class RigolMSO:
    def __init__(self, resource_manager_addr):
        import pyvisa
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        self.inst.timeout = 5000

    def set_channel_display(self, state, channel=1):
        s = "ON" if state else "OFF"
        self.inst.write(f":CHANnel{channel}:DISPlay {s}")

    def get_channel_state(self, channel=1):
        try:
            resp = self.inst.query(f":CHANnel{channel}:DISPlay?")
            return "1" in resp or "ON" in resp.upper()
        except: return False

    def get_run_state(self):
        try:
            resp = self.inst.query(":TRIGger:STATus?")
            return "STOP" not in resp.upper()
        except: return False

    def auto_scale(self): 
        self.inst.write(":AUToscale")
        
    def run(self): 
        self.inst.write(":RUN")
        
    def stop(self): 
        self.inst.write(":STOP")

    def get_measure(self, type, channel=1):
        old_timeout = self.inst.timeout
        self.inst.timeout = 500 
        try:
            val = float(self.inst.query(f":MEASure:ITEM? {type},CHANnel{channel}"))
            self.inst.timeout = old_timeout
            return val
        except:
            self.inst.timeout = old_timeout
            return None

    def get_waveform_data(self, channel=1):
        self.inst.write(f":WAV:SOUR CHANnel{channel}")
        self.inst.write(":WAV:MODE NORM")
        self.inst.write(":WAV:FORM BYTE")
        
        try:
            pre = self.inst.query(":WAV:PRE?").split(',')
            if len(pre) < 10: return [], []
            
            x_inc, x_orig, x_ref = float(pre[4]), float(pre[5]), float(pre[6])
            y_inc, y_orig, y_ref = float(pre[7]), float(pre[8]), float(pre[9])
            
            raw = self.inst.query_binary_values(":WAV:DATA?", datatype='B', container=np.array)
            
            t = (np.arange(len(raw)) - x_ref) * x_inc + x_orig
            v = (raw.astype(float) - y_orig - y_ref) * y_inc
            return t.tolist(), v.tolist()
        except:
            return [], []

    def close(self): 
        try: self.inst.write(":SYSTem:KEY:FORCe") 
        except: pass
        self.inst.close()