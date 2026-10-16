#include <Wire.h>
#include "FDC2214.h"

/*
  FDC2214 4-Channel Direct Reading - Raw Capacitance Output Only
  Reads 4 nodes directly from FDC2214 channels (CH0, CH1, CH2, CH3) without MUX.
  Removed median and delta C calculations to reduce RAM usage.
  Baseline and delta C/C computations are done in Python (real_serial_read_diff.py).
  Output format to Serial (one line per node):
  Timestamp,Row_index,Column_index,Raw_Capacitance_pF
  
  Channel mapping:
  CH0 -> Node (0,0)
  CH1 -> Node (0,1)
  CH2 -> Node (1,0)
  CH3 -> Node (1,1)
*/

FDC2214 capsense(FDC2214_I2C_ADDR_0);

// 4 nodes mapped to FDC channels
#define NUM_NODES 4
const int NODE_CHANNEL_MAP[NUM_NODES] = {0, 1, 2, 3};  // CH0, CH1, CH2, CH3
const int NODE_ROW_MAP[NUM_NODES] = {0, 0, 1, 1};      // Row indices
const int NODE_COL_MAP[NUM_NODES] = {0, 1, 0, 1};      // Column indices

// Timing constants
#define CHANNEL_SWITCH_DELAY_MS 2  // Small delay when switching channels

// -------- Setup --------
void setup() {
  Wire.begin();
  Serial.begin(115200);
  delay(300);

  Serial.println("\nFDC2214 4-Channel Direct Reading - Raw Capacitance Output");

  // Initialize FDC2214 with all 4 channels enabled and autoscan
  // 0x0F = binary 1111 = all channels (CH0, CH1, CH2, CH3) enabled
  // 0x0F = autoscan sequence through all enabled channels
  // 0x01 = 1 MHz deglitch (reduced from 10MHz to reduce noise)
  // true = internal oscillator
  bool ok = capsense.begin(
    0x0F,   // All 4 channels enabled (CH0, CH1, CH2, CH3)
    0x0F,   // Autoscan through all enabled channels
    0x01,   // 1 MHz deglitch (reduced from 10MHz to reduce noise)
    true    // internal oscillator
  );
  Serial.println(ok ? "Sensor OK" : "Sensor FAIL");

  // Let FDC stabilize
  delay(200);
  
  Serial.println("Timestamp,Row_index,Column_index,Raw_Capacitance_pF");
}

// -------- Capacitance Conversion --------
double computeCap_pf(unsigned long reading) {
  const double fref = 40000000.0;  // 40 MHz internal reference
  const double L = 18e-6;          // 18 uH inductor
  const double Cboard = 33e-12;    // 33 pF fixed board capacitor
  const double Cpar = 3e-12;       // parasitics (adjust if needed)

  // Convert raw code → frequency
  double fs = (fref * (double)reading) / 268435456.0; // 2^28

  // LC resonance equation → total capacitance
  double Ctotal = 1.0 / ((2.0 * M_PI * fs) * (2.0 * M_PI * fs) * L);

  // Remove board + parasitic capacitance
  double Csensor = Ctotal - (Cboard + Cpar);

  return Csensor * 1e12; // convert to picofarads
}

// -------- Main Loop --------
void loop() {
  unsigned long timestamp = millis();
  
  // Read all 4 channels directly (no MUX needed)
  for (int i = 0; i < NUM_NODES; i++) {
    int channel = NODE_CHANNEL_MAP[i];
    int row = NODE_ROW_MAP[i];
    int col = NODE_COL_MAP[i];
    
    // Read directly from FDC channel (autoscan handles channel switching)
    unsigned long reading = capsense.getReading28(channel);
    
    // Convert to capacitance in pF
    double cap_pf = computeCap_pf(reading);
    
    // Output: Timestamp,Row_index,Column_index,Raw_Capacitance_pF
    // No baseline or delta C calculations - done in Python to save RAM
    Serial.print(timestamp);
    Serial.print(",");
    Serial.print(row);
    Serial.print(",");
    Serial.print(col);
    Serial.print(",");
    Serial.println(cap_pf, 3);  // 3 decimal places for capacitance
    
    // Small delay between channel reads
    delay(CHANNEL_SWITCH_DELAY_MS);
  }
  
  // Small delay between full scans
  delay(2);
}
