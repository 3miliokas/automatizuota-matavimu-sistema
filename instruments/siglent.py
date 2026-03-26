import pyvisa

class SiglentSDG:
    def __init__(self, address):
        self.address = address
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.address)
        self.inst.timeout = 2000

    def apply_waveform(self, wave_type, freq, amp, offset, phase, duty, sym):
        wvtp_map = {"Sine": "SINE", "Square": "SQUARE", "Ramp": "RAMP", 
                    "Pulse": "PULSE", "Noise": "NOISE", "Arb": "ARB"}
        wvtp = wvtp_map.get(wave_type, "SINE")

        cmd = f"C1:BSWV WVTP,{wvtp}"
        if wvtp != "NOISE":
            cmd += f",FRQ,{freq},PHSE,{phase}"
        cmd += f",AMP,{amp},OFST,{offset}"
        
        if wvtp in ["SQUARE", "PULSE"]:
            cmd += f",DUTY,{duty}"
        elif wvtp == "RAMP":
            cmd += f",SYM,{sym}"

        self.inst.write(cmd)
        self.inst.write("C1:OUTP ON")
        
        try:
            self.inst.control_ren(pyvisa.constants.VI_GPIB_REN_DEASSERT_GTL)
        except:
            pass

    def close(self):
        self.inst.close()