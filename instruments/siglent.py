import pyvisa
import re

class SiglentSDG:
    """
    Aparatūrinė tvarkyklė (Driver), skirta valdyti Siglent SDG serijos (pvz., SDG1000) 
    funkcinių/savavališkų formų signalų generatorius.
    Komunikacija vykdoma naudojant gamintojo specifines SCPI komandas per VISA protokolą.
    """
    def __init__(self, resource_manager_addr, logger=None):
        self.logger = logger
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        
        # Generatoriaus komandos paprastai įvykdomos greitai, todėl pakanka 2 s timeout
        self.inst.timeout = 2000

    def close(self):
        """Saugiai nutraukia VISA sesiją ir atlaisvina ryšio prievadą."""
        try:
            self.inst.close()
            self.rm.close()
        except: pass

    def write(self, cmd):
        """Išsiunčia komandą į prietaisą be atsakymo laukimo."""
        if self.logger: self.logger(f"SDG TX: {cmd}")
        self.inst.write(cmd)

    def query(self, cmd):
        """Išsiunčia užklausą ir laukia tekstinio atsakymo iš prietaiso."""
        if self.logger: self.logger(f"SDG TX: {cmd}")
        resp = self.inst.query(cmd).strip()
        if self.logger: self.logger(f"SDG RX: {resp}")
        return resp

    def get_output_state(self, channel=1):
        """
        Nuskaito fizinę nurodyto kanalo išvesties būseną (Įjungta/Išjungta).
        Grąžina True (jei ON) arba False (jei OFF).
        """
        try:
            resp = self.query(f"C{channel}:OUTP?")
            return "ON" in resp.upper()
        except: return False

    def get_waveform_params(self, channel=1):
        """
        Nuskaito visus aktyvaus signalo parametrus (BSWV - Basic Waveform).
        Iškoduoja prietaiso grąžintą ilgą SCPI eilutę į patogų Python žodyną (Dictionary),
        pašalindamas matavimo vienetus (pvz., '1000HZ' -> '1000').
        """
        try:
            resp = self.query(f"C{channel}:BSWV?")
            
            # Pašalinama pradinė komandos echo dalis iš atsakymo (pvz., 'C1:BSWV ')
            resp = re.sub(rf"C{channel}:BSWV\s*", "", resp).strip()
            
            # Komponentai atskirti kableliais (raktas, reikšmė, raktas, reikšmė...)
            parts = resp.split(",")
            params = {}
            
            for i in range(0, len(parts)-1, 2):
                key = parts[i].strip()
                val = parts[i+1].strip()
                
                # Išvalomi fiziniai vienetai paliekant tik grynas skaitines vertes.
                # Naudojamos reguliariosios išraiškos (Regex), ignoruojant raidžių registrą (IGNORECASE).
                if key in ["FRQ", "AMP", "OFST", "PHSE", "DUTY", "SYM", "DLY"]:
                    val = re.sub(r"(HZ|V|S|DEG|%)", "", val, flags=re.IGNORECASE).strip()
                    
                params[key] = val
                
            return params
        except: return {}

    def set_output(self, state, channel=1):
        """Įjungia (ON) arba išjungia (OFF) fizinę BNC išvestį prietaiso priekyje."""
        s = "ON" if state else "OFF"
        self.write(f"C{channel}:OUTP {s}")

    def sync_eqphase(self):
        """
        Programiškai sinchronizuoja abiejų kanalų fazes.
        Priverstinai nustato CH1 ir CH2 pradinę fazę į 0 laipsnių.
        """
        self.write("C1:BSWV PHSE,0")
        self.write("C2:BSWV PHSE,0")

    def apply_waveform(self, wave_type, freq_mode, freq_val, amp_mode, amp_val, off_val, phase, duty, sym, delay, stdev, mean, channel=1):
        """
        Sukonstruoja ir išsiunčia kompleksinę SCPI komandą, nustatančią
        visus signalo formos (Waveform) parametrus vienu kreipimusi.
        Parametrų sąrašas priklauso nuo pasirinktos signalo formos (Sine, Square, Noise ir kt.).
        """
        wv = wave_type.upper()
        
        # Bazinė komandos struktūra signalo tipui nustatyti
        cmd = f"C{channel}:BSWV WVTP,{wv}"
        
        # Priverstinai nustatoma, kad apkrovos varža išvestyje yra didelė (High-Z),
        # užtikrinant, kad rodoma amplitudė ekrane atitiktų realią amplitudę.
        self.write(f"C{channel}:OUTP LOAD,HZ")

        # Jei signalas - baltojo triukšmo (Noise), nustatomas tik standartinis nuokrypis ir vidurkis
        if wv == "NOISE":
            cmd += f",STDEV,{stdev},MEAN,{mean}"
        else:
            # Standartiniams signalams konstruojama parametrų grandinė
            if freq_mode == "FRQ": 
                cmd += f",FRQ,{freq_val}"
            else: 
                cmd += f",PERI,{freq_val}"
                
            if amp_mode == "AMP": 
                cmd += f",AMP,{amp_val},OFST,{off_val}"
            else: 
                cmd += f",HLEV,{amp_val},LLEV,{off_val}"
                
            cmd += f",PHSE,{phase}"
            
            # Prijungiami specifiniai parametrai, priklausantys nuo signalo formos
            if wv == "SQUARE": cmd += f",DUTY,{duty}"
            if wv == "RAMP": cmd += f",SYM,{sym}"
            if wv == "PULSE": cmd += f",DLY,{delay}"
            
        # Išsiunčiama galutinė pilnai sukonstruota eilutė
        self.write(cmd)