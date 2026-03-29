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
        try:
            val = self.inst.query(f":MEASure:ITEM? {item},CHANnel{channel}")
            return float(val)
        except ValueError:
            return 0.0

    def get_waveform_data(self, channel=1):
        self.inst.write(f":WAVeform:SOURce CHANnel{channel}")
        self.inst.write(":WAVeform:MODE NORMal")
        self.inst.write(":WAVeform:FORMat BYTE")
        
        preamble = self.inst.query(":WAVeform:PREamble?").split(',')
        xinc = float(preamble[4])
        xorig = float(preamble[5])
        yinc = float(preamble[7])
        yorig = int(preamble[8])
        yref = int(preamble[9])
        
        rawdata = self.inst.query_binary_values(":WAVeform:DATA?", datatype='B', header_fmt='ieee', expect_termination=False)
        data = np.array(rawdata)
        
        volts = (data - yorig - yref) * yinc
        time = np.arange(len(volts)) * xinc + xorig
        
        return time.tolist(), volts.tolist()

    def get_screenshot(self):
        """Parsiunčia ekrano nuotrauką iš oscilografo PNG formatu."""
        self.inst.timeout = 5000 
        self.inst.write(":DISPlay:DATA? ON,OFF,PNG")
        raw_data = self.inst.read_raw()
        
        # TMC antraštės šalinimas (formatas: #NXXXXXX)
        if raw_data.startswith(b'#'):
            header_len_char = raw_data[1:2].decode()
            if header_len_char.isdigit():
                header_len = int(header_len_char)
                image_data = raw_data[2 + header_len:]
                return image_data
        return raw_data

    def close(self):
        self.inst.close()