import pyvisa
import numpy as np

class RigolMSO:
    def __init__(self, address):
        self.address = address
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.address)
        self.inst.timeout = 3000

    def auto_scale(self):
        self.inst.write(":AUToscale")

    def run(self):
        self.inst.write(":RUN")

    def stop(self):
        self.inst.write(":STOP")

    def set_timebase(self, scale):
        self.inst.write(f":TIMebase:MAIN:SCALe {scale}")

    def set_channel_scale(self, channel, scale):
        self.inst.write(f":CHANnel{channel}:SCALe {scale}")

    def get_measure(self, item, channel=1):
        """Palaikomi item: VPP, VMAX, VMIN, VAMP, FREQ, PER, RIS, FALL"""
        try:
            val = self.inst.query(f":MEASure:ITEM? {item},CHANnel{channel}")
            return float(val)
        except ValueError:
            return 0.0

    def get_waveform_data(self, channel=1):
        """Nuskaito ekrano buferį (iki 1200 taškų) ir konvertuoja į realią įtampą."""
        self.inst.write(f":WAVeform:SOURce CHANnel{channel}")
        self.inst.write(":WAVeform:MODE NORMal")
        self.inst.write(":WAVeform:FORMat BYTE")
        
        preamble = self.inst.query(":WAVeform:PREamble?").split(',')
        xinc = float(preamble[4])
        xorig = float(preamble[5])
        yinc = float(preamble[7])
        yorig = int(preamble[8])
        yref = int(preamble[9])
        
        # Rigol siunčia TMC antraštę (#800000000), header_fmt='ieee' ją apdoroja
        rawdata = self.inst.query_binary_values(":WAVeform:DATA?", datatype='B', header_fmt='ieee', expect_termination=False)
        data = np.array(rawdata)
        
        # Konversija pagal Rigol Programming Guide algoritmą
        volts = (data - yorig - yref) * yinc
        time = np.arange(len(volts)) * xinc + xorig
        
        return time.tolist(), volts.tolist()

    def close(self):
        self.inst.close()