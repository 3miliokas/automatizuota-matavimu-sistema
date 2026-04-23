class SiglentSDG:
    def __init__(self, resource_manager_addr):
        import pyvisa
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        self.inst.timeout = 5000

    def get_output_state(self, channel=1):
        try:
            resp = self.inst.query(f"C{channel}:OUTP?")
            return "ON" in resp.upper()
        except: return False

    def get_waveform_params(self, channel=1):
        """Nuskaito ir grąžina pilną kanalo parametrų eilutę."""
        try:
            return self.inst.query(f"C{channel}:BSWV?").strip()
        except:
            return ""

    def set_output(self, state, channel=1):
        s = "ON" if state else "OFF"
        self.inst.write(f"C{channel}:OUTP {s}")
        self.inst.write("SYSTem:LOCal")

    def apply_waveform(self, type, freq, amp, offset, phase, duty=50, sym=50, channel=1):
        self.inst.write(f"C{channel}:BSWV WVTP,{type},FRQ,{freq},AMP,{amp},OFST,{offset},PHSE,{phase}")
        if type.upper() == "SQUARE": self.inst.write(f"C{channel}:BSWV DUTY,{duty}")
        if type.upper() == "RAMP": self.inst.write(f"C{channel}:BSWV SYM,{sym}")
        self.inst.write("SYSTem:LOCal")

    def close(self):
        try: self.inst.write("SYSTem:LOCal")
        except: pass
        self.inst.close()