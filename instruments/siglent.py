import pyvisa
import re

class SiglentSDG:
    def __init__(self, resource_manager_addr, logger=None):
        self.logger = logger
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        self.inst.timeout = 2000

    def close(self):
        try:
            self.inst.close()
            self.rm.close()
        except: pass

    def write(self, cmd):
        if self.logger: self.logger(f"SDG TX: {cmd}")
        self.inst.write(cmd)

    def query(self, cmd):
        if self.logger: self.logger(f"SDG TX: {cmd}")
        resp = self.inst.query(cmd).strip()
        if self.logger: self.logger(f"SDG RX: {resp}")
        return resp

    def get_output_state(self, channel=1):
        try:
            resp = self.query(f"C{channel}:OUTP?")
            return "ON" in resp.upper()
        except: return False

    def get_waveform_params(self, channel=1):
        try:
            resp = self.query(f"C{channel}:BSWV?")
            resp = re.sub(rf"C{channel}:BSWV\s*", "", resp).strip()
            parts = resp.split(",")
            params = {}
            for i in range(0, len(parts)-1, 2):
                key = parts[i].strip()
                val = parts[i+1].strip()
                if key in ["FRQ", "AMP", "OFST", "PHSE", "DUTY", "SYM", "DLY"]:
                    val = re.sub(r"(HZ|V|S|DEG|%)", "", val, flags=re.IGNORECASE).strip()
                params[key] = val
            return params
        except: return {}

    def set_output(self, state, channel=1):
        s = "ON" if state else "OFF"
        self.write(f"C{channel}:OUTP {s}")

    def sync_eqphase(self):
        self.write("C1:BSWV PHSE,0")
        self.write("C2:BSWV PHSE,0")

    def apply_waveform(self, wave_type, freq_mode, freq_val, amp_mode, amp_val, off_val, phase, duty, sym, delay, stdev, mean, channel=1):
        wv = wave_type.upper()
        cmd = f"C{channel}:BSWV WVTP,{wv}"
        self.write(f"C{channel}:OUTP LOAD,HZ")

        if wv == "NOISE":
            cmd += f",STDEV,{stdev},MEAN,{mean}"
        else:
            if freq_mode == "FRQ": cmd += f",FRQ,{freq_val}"
            else: cmd += f",PERI,{freq_val}"
            if amp_mode == "AMP": cmd += f",AMP,{amp_val},OFST,{off_val}"
            else: cmd += f",HLEV,{amp_val},LLEV,{off_val}"
            cmd += f",PHSE,{phase}"
            if wv == "SQUARE": cmd += f",DUTY,{duty}"
            if wv == "RAMP": cmd += f",SYM,{sym}"
            if wv == "PULSE": cmd += f",DLY,{delay}"
            
        self.write(cmd)