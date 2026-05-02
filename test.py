import serial
import time

PORT = 'COM3'  # Keisti į savo prievadą
BAUDRATE = 9600

def run_extended_raw_test():
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=0.1)
        ser.setRTS(False) 
        ser.setDTR(True)  
        time.sleep(0.5)
        
        print("--- ATIDARYTAS PRIEVADAS ---")
        ser.reset_input_buffer()
        
        print("Siunčiama 'u' (Remote Mode)...")
        ser.write(b'u')
        ser.flush()
        
        # Suplanuotos komandos: (laikas_sekundėmis, baitas, pavadinimas)
        commands = [
            (3.0, b'f', "Volts (V)"),
            (8.0, b'l', "AC"),
            (13.0, b'm', "DC"),
            (18.0, b'n', "milliVolts (mV)"),
            (23.0, b'i', "Ohms (OHM) - Auto-range testas"),
            (31.0, b'a', "Range UP"),
            (36.0, b'b', "Range DOWN"),
            (41.0, b'c', "Auto Range"),
            (48.0, b'd', "Amps (A)"),
            (53.0, b'e', "milliAmps (mA)"),
            (58.0, b'j', "Frequency (Hz)"),
            (64.0, b'f', "Volts (V) - Grįžimas"),
            # Dvigubų komandų (SHIFT) testavimas
            (70.0, b'k', "SHIFT (NULL aktyvavimui)"),
            (70.2, b'i', "OHM (NULL aktyvavimui)"),
            (78.0, b'k', "SHIFT (HOLD aktyvavimui)"),
            (78.2, b'j', "FREQ (HOLD aktyvavimui)"),
            (85.0, b'f', "Volts (V) - Reset po Hold"),
            (90.0, b'g', "OPERATE (Maitinimo perjungimas)"),
        ]
        
        start_time = time.time()
        cmd_index = 0
        
        print("\nPradedamas srauto skaitymas (trūks 100 sek.)...")
        while time.time() - start_time < 100.0:
            current_time = time.time() - start_time
            
            # Ar atėjo laikas siųsti komandą?
            if cmd_index < len(commands) and current_time > commands[cmd_index][0]:
                delay, cmd_byte, cmd_name = commands[cmd_index]
                print(f"\n[>>> {current_time:.2f}s] SIUNČIAMA KOMANDA: {cmd_name} ({cmd_byte})")
                ser.write(cmd_byte)
                ser.flush()
                cmd_index += 1
            
            # Duomenų nuskaitymas ir atvaizdavimas
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"[{current_time:.2f}s] RX Hex: {data.hex():<30} | ASCII: {repr(data)}")
            
            time.sleep(0.05)
            
    except Exception as e:
        print(f"Klaida: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\n--- PRIEVADAS UŽDARYTAS ---")

if __name__ == "__main__":
    run_extended_raw_test()