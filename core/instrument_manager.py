import threading
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class InstrumentManager:
    """
    Centrinė aparatūros valdymo klasė (Sistemos branduolys).
    Atsakinga už fizinių prietaisų sesijų kūrimą, nutraukimą bei saugų
    lygiagretų valdymą. Naudoja abipusės atskirties (Mutex Lock) mechanizmą,
    kad išvengtų aparatūrinių konfliktų vykdant procesus skirtingose gijose.
    """
    def __init__(self, logger=None):
        self.logger = logger
        
        # Saugumo užraktas. Kai viena gija (pvz., fono skenavimas) atlieka operaciją,
        # kitos gijos laukia, kol užraktas bus atleistas.
        self.lock = threading.Lock()
        
        # Prietaisų instancijų kintamieji
        self.gen = self.osc = self.tti = self.esc = None

    def connect_gen(self, addr):
        """Prijungia Siglent signalų generatorių per nurodytą VISA adresą."""
        with self.lock:
            if self.gen: self.gen.close()
            try:
                self.gen = SiglentSDG(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"GEN Klaida: {e}")

    def connect_osc(self, addr):
        """Prijungia Rigol oscilografą per nurodytą VISA adresą."""
        with self.lock:
            if self.osc: self.osc.close()
            try:
                self.osc = RigolMSO(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"OSC Klaida: {e}")

    def connect_tti(self, port):
        """
        Prijungia TTi 1604 multimetrą per nurodytą COM prievadą.
        Apsaugo nuo COM prievado užimtumo konflikto, jei Escort multimetras
        bando naudoti tą patį fizinį prievadą.
        """
        with self.lock:
            # Saugos mechanizmas: Uždaro Escort, jei jis naudoja tą patį COM prievadą
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
        Apsaugo nuo COM prievado užimtumo konflikto, jei TTi multimetras
        bando naudoti tą patį fizinį prievadą.
        """
        with self.lock:
            # Saugos mechanizmas: Uždaro TTi, jei jis naudoja tą patį COM prievadą
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
        Iškviečiama išjungiant programą arba perskenuojant magistrales.
        """
        with self.lock:
            if self.gen: self.gen.close()
            if self.osc: self.osc.close()
            if self.tti: self.tti.close()
            if self.esc: self.esc.close()