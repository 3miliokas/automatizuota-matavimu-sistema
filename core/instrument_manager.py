import threading
from instruments.siglent import SiglentSDG
from instruments.rigol import RigolMSO
from instruments.tti import TTi1604
from instruments.escort import Escort3136A

class InstrumentManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.lock = threading.Lock()
        self.gen = self.osc = self.tti = self.esc = None

    def connect_gen(self, addr):
        with self.lock:
            if self.gen: self.gen.close()
            try:
                self.gen = SiglentSDG(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"GEN Klaida: {e}")

    def connect_osc(self, addr):
        with self.lock:
            if self.osc: self.osc.close()
            try:
                self.osc = RigolMSO(addr, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"OSC Klaida: {e}")

    def connect_tti(self, port):
        with self.lock:
            # Uždaro Escort, jei jis naudoja tą patį COM prievadą
            if self.esc and getattr(self.esc, 'port', None) == port:
                self.esc.close()
                self.esc = None
                
            if self.tti: self.tti.close()
            try:
                self.tti = TTi1604(port, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"TTi Klaida ({port}): {e}")

    def connect_esc(self, port):
        with self.lock:
            # Uždaro TTi, jei jis naudoja tą patį COM prievadą
            if self.tti and getattr(self.tti, 'port', None) == port:
                self.tti.close()
                self.tti = None
                
            if self.esc: self.esc.close()
            try:
                self.esc = Escort3136A(port, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger(f"Escort Klaida ({port}): {e}")

    def close_all(self):
        with self.lock:
            if self.gen: self.gen.close()
            if self.osc: self.osc.close()
            if self.tti: self.tti.close()
            if self.esc: self.esc.close()