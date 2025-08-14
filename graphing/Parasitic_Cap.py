import serial
import math

# ==== User constants ====
PORT = "COM8"         # Change to your Arduino serial port
BAUD = 115200         # Must match Arduino's Serial.begin
FREF = 40_000_000     # Reference clock frequency (Hz)
DATA_BITS = 28
L = 18e-6             # Inductance in Henries
# ========================

def raw_to_frequency(raw_data):
    """Convert 28-bit raw reading to frequency (Hz)."""
    return (raw_data * FREF) / (1 << DATA_BITS)

def frequency_to_total_capacitance(freq_hz):
    """Convert frequency to total capacitance (F)."""
    return 1.0 / (L * (2 * math.pi * freq_hz)**2)

# ---- Calibration Step ----
def calibrate_c_fixed(ser):
    """Read one shorted-plate sample to determine fixed parallel C."""
    print("Waiting for shorted-plate reading...")
    line = ser.readline().decode().strip()
    raw_values = [int(x) for x in line.split(",")]
    # Use channel 0 here; change index if you want a different channel
    raw_short = raw_values[0]
    freq_short = raw_to_frequency(raw_short)
    c_fixed = frequency_to_total_capacitance(freq_short)
    print(f"C_FIXED = {c_fixed*1e12:.3f} pF")
    return c_fixed

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)

    # ---- Step 1: Calibrate ----
    C_FIXED = calibrate_c_fixed(ser)
    print("Remove short and start live readings...")

    # ---- Step 2: Continuous readings ----
    while True:
        line = ser.readline().decode().strip()
        if not line:
            continue
        try:
            raw_values = [int(x) for x in line.split(",")]
            for ch, raw in enumerate(raw_values):
                freq = raw_to_frequency(raw)
                c_total = frequency_to_total_capacitance(freq)
                c_sense = c_total - C_FIXED
                print(f"CH{ch}: {freq:.3f} Hz, {c_sense*1e12:.3f} pF")
        except ValueError:
            # Ignore bad lines
            continue

if __name__ == "__main__":
    main()
