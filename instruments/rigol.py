import numpy as np

class RigolMSO:
    """
    Aparatūrinė tvarkyklė (Driver), skirta valdyti Rigol MSO/DS serijos oscilografus.
    Komunikacija vykdoma naudojant standartizuotas SCPI komandas per VISA protokolą.
    Palaiko ne tik bazinį valdymą, bet ir greitą binarinių duomenų (oscilogramų,
    ekrano kopijų) perdavimą.
    """
    def __init__(self, resource_manager_addr, logger=None):
        self.logger = logger
        import pyvisa
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_manager_addr)
        
        # Nustatomas ilgesnis 5 sekundžių laukimo laikas (timeout), 
        # būtinas didelių binarinių duomenų masyvų (ekrano kopijų, FFT) parsisiuntimui
        self.inst.timeout = 5000

    def close(self):
        """Saugiai nutraukia VISA sesiją ir atlaisvina resursus."""
        try:
            self.inst.close()
            self.rm.close()
        except: pass

    def write(self, cmd):
        """Išsiunčia SCPI komandą be atsakymo laukimo."""
        if self.logger: self.logger(f"MSO TX: {cmd}")
        self.inst.write(cmd)

    def query(self, cmd):
        """Išsiunčia SCPI užklausą ir grąžina tekstinį prietaiso atsakymą."""
        if self.logger: self.logger(f"MSO TX: {cmd}")
        resp = self.inst.query(cmd).strip()
        
        # Filtruojamas žurnalo (logger) pildymas.
        # Binarinių duomenų užklausos ignoruojamos, kad neužterštų konsolės neatpažįstamais simboliais.
        if "WAV:DATA?" not in cmd and "WAV:PRE?" not in cmd and "DISP:DATA?" not in cmd:
            if self.logger: self.logger(f"MSO RX: {resp}")
        return resp

    def set_channel_display(self, state, channel=1):
        """Įjungia arba išjungia fizinį oscilografo kanalo atvaizdavimą ekrane."""
        s = "ON" if state else "OFF"
        self.write(f":CHANnel{channel}:DISPlay {s}")

    def get_channel_state(self, channel=1):
        """Nuskaito, ar nurodytas kanalas šiuo metu yra aktyvus."""
        try:
            resp = self.query(f":CHANnel{channel}:DISPlay?")
            return "1" in resp or "ON" in resp.upper()
        except: return False

    def get_run_state(self):
        """Nuskaito trigerio būseną (ar prietaisas matuoja - RUN, ar sustabdytas - STOP)."""
        try:
            resp = self.query(":TRIGger:STATus?")
            return "STOP" not in resp.upper()
        except: return False

    def auto_scale(self): 
        """Inicijuoja automatinį prietaiso ašių kalibravimą pagal įėjimo signalą."""
        self.write(":AUToscale")
        
    def run(self): 
        self.write(":RUN")
        
    def stop(self): 
        self.write(":STOP")

    def get_measure(self, type, channel=1):
        """
        Nuskaito specifinį matavimo parametrą (pvz., VPP, FREQ).
        Saugumo sumetimais laikinai sumažinamas timeout iki 500 ms, 
        kad prietaisui nepavykus atlikti matavimo (pvz., nesant signalo), 
        programa neužšaltų 5 sekundėms.
        """
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
        """
        Atsisiunčia pilną oscilogramos laiko ir įtampos matricą (Time domain).
        Naudoja optimizuotą binarinį perdavimą (BYTE formatu) greitaveikai užtikrinti.
        """
        self.write(f":WAV:SOUR CHANnel{channel}")
        self.write(":WAV:MODE NORM")
        self.write(":WAV:FORM BYTE")
        try:
            # Nuskaitoma preambulė, kurioje saugomi ašių mastelio ir poslinkio koeficientai
            pre = self.query(":WAV:PRE?").split(',')
            if len(pre) < 10: return [], []
            
            # Ištraukiami laiko (X) ir įtampos (Y) transformacijos koeficientai
            x_inc, x_orig, x_ref = float(pre[4]), float(pre[5]), float(pre[6])
            y_inc, y_orig, y_ref = float(pre[7]), float(pre[8]), float(pre[9])
            
            if self.logger: self.logger("MSO TX: :WAV:DATA? (Binary Transfer)")
            
            # Surenkamas žalias (raw) binarinis duomenų masyvas į greitą numpy struktūrą
            raw = self.inst.query_binary_values(":WAV:DATA?", datatype='B', container=np.array, header_fmt='ieee')
            
            # Matematinių transformacijų pritaikymas: raw bitai paverčiami fiziniais vienetais (Voltais)
            v = (raw - y_orig - y_ref) * y_inc
            
            # Sukuriamas atitinkamas laiko ašies masyvas (Sekundėmis)
            t = np.arange(len(v)) * x_inc + x_orig
            
            return t, v
        except Exception as e:
            if self.logger: self.logger(f"MSO WAV Error: {e}")
            return [], []

    def get_screenshot(self):
        """
        Parsisiunčia dabartinį prietaiso ekrano vaizdą PNG formatu.
        Grąžina binarinį (bytes) masyvą, kurį vėliau galima įrašyti tiesiai į disko failą.
        """
        try:
            if self.logger: self.logger("MSO TX: :DISP:DATA? ON,OFF,PNG (Binary Transfer)")
            raw = self.inst.query_binary_values(":DISP:DATA? ON,OFF,PNG", datatype='B', container=bytes, header_fmt='ieee')
            return raw
        except Exception as e:
            if self.logger: self.logger(f"MSO Screenshot Error: {e}")
            return b""