import threading
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class InstrumentManager:
    """
    Centrinė aparatūros valdymo klasė (Sistemos branduolys).
    Ši klasė sukuria "Tiltą" tarp grafinės vartotojo sąsajos (GUI) ir fizinių prietaisų tvarkyklių.
    
    Ypatinga savybė: Naudojamas abipusės atskirties (Mutex Lock) mechanizmas. 
    Tai apsaugo programą ir fizinius prietaisus nuo vadinamųjų "Race Condition" klaidų, kai kelios 
    gijos (pavyzdžiui: vartotojas spaudžia mygtuką, o fono loggeris bando siųsti užklausą) 
    bando vienu metu pasiekti tą patį prietaisą per tą patį ryšio kabelį.
    """
    def __init__(self, logger=None):
        self.logger = logger
        
        # Sukuriamas globalus sistemos užraktas (Lock). 
        # Naudojamas "with self.lock:" bloke visuose valdikliuose (Controllers).
        # Kol viena operacija neužbaigia darbo (pvz., nuskaito atsakymą), kitos turi laukti.
        self.lock = threading.Lock()
        
        # Pradiniai prietaisų kintamieji, saugantys prisijungimo sesijas
        self.gen = None  # Siglent SDG (Generatorius)
        self.osc = None  # Rigol MSO (Oscilografas)
        self.tti = None  # TTi 1604 (Multimetras A)
        self.esc = None  # Escort 3136A (Multimetras B)

    def connect_gen(self, addr):
        """
        Prijungia Siglent signalų generatorių per nurodytą VISA adresą.
        Prieš prisijungiant naujai, visada bandoma saugiai uždaryti seną sesiją.
        """
        with self.lock:
            if self.gen: self.gen.close()
            try:
                self.gen = SiglentSDG(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"GEN Klaida: {e}")

    def connect_osc(self, addr):
        """
        Prijungia Rigol oscilografą per nurodytą VISA adresą.
        """
        with self.lock:
            if self.osc: self.osc.close()
            try:
                self.osc = RigolMSO(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"OSC Klaida: {e}")

    def connect_tti(self, port):
        """
        Prijungia TTi 1604 multimetrą per nurodytą COM prievadą (RS-232 / USB).
        
        Apsaugos mechanizmas: Windows sistemoje neįmanoma prie vieno COM prievado 
        vienu metu prisijungti dviem programoms (ar dviejų tipų tvarkyklėms). 
        Ši logika užtikrina, kad jei vartotojas per klaidą priskyrė TTi prietaisui 
        tą patį COM prievadą kaip ir Escort prietaisui, senasis ryšys (su Escort) 
        bus priverstinai nutrauktas prieš sukuriant naują (su TTi).
        """
        with self.lock:
            # Tikrina, ar Escort egzistuoja ir ar jo nustatytas prievadas sutampa su dabar prašomu
            if self.esc and getattr(self.esc, 'port', None) == port:
                self.esc.close()
                self.esc = None
                
            if self.tti: self.tti.close()
            try:
                self.tti = TTi1604(port, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"TTi Klaida ({port}): {e}")

    def connect_esc(self, port):
        """
        Prijungia Escort 3136A multimetrą per nurodytą COM prievadą.
        Lygiai taip pat kaip ir connect_tti metode, apsaugo nuo COM prievado užimtumo
        konflikto su TTi 1604 multimetru.
        """
        with self.lock:
            # Tikrina, ar TTi egzistuoja ir ar jo prievadas sutampa su dabar prašomu Escort'ui
            if self.tti and getattr(self.tti, 'port', None) == port:
                self.tti.close()
                self.tti = None
                
            if self.esc: self.esc.close()
            try:
                self.esc = Escort3136A(port, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"Escort Klaida ({port}): {e}")

    def close_all(self):
        """
        Saugiai uždaro visus atidarytus ryšio kanalus su fiziniais prietaisais.
        Šis metodas iškviečiamas automatiškai išjungiant programą arba
        vartotojui paspaudus mygtuką "Skenuoti VISA ir COM", kad prieš pradedant
        naują skenavimą joks prievadas nebūtų užrakintas operacinėje sistemoje (Windows/Linux).
        """
        with self.lock:
            if self.gen: self.gen.close()
            if self.osc: self.osc.close()
            if self.tti: self.tti.close()
            if self.esc: self.esc.close()