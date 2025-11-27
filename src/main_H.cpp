#include <Wire.h>
#include "FDC2214.h"

/*
  FDC2214 8x8 Grid Scanning - Raw Capacitance Output
  Two 8:1 analog multiplexers (MUX1 for rows, MUX2 for columns) connected to FDC2214 CH0.
  Output format to Serial (one line per node):
  Timestamp,Row_index,Column_index,Raw_Capacitance_pF
  where:
    Row_index = MUX1 state (0-7)
    Column_index = MUX2 state (0-7)
    Raw_Capacitance_pF = capacitance value in picofarads (computed from FDC2214 raw reading)
  
  Note: Baseline calculation and ΔC/C computation are done in post-processing (real_serial_read_diff.py)
*/

// MUX pin mapping (3 select lines for 8:1 mux)
// SN74HC4051 follows this format: C B A == S2 S1 S0
#define MUX1_S0 2 // LSB   (Row MUX)
#define MUX1_S1 3
#define MUX1_S2 4 // MSB
#define MUX2_S0 5 // LSB   (Column MUX)
#define MUX2_S1 6
#define MUX2_S2 7 // MSB

// Constants
#define TOTAL_MUX_STATES 8   // 8:1 multiplexers (8 rows, 8 columns)
#define ROW_SETTLE_US 3000   // Reduced from 8000: Settle time for row switching (optimized for 4 nodes)
#define COL_SETTLE_US 3000   // Reduced from 8000: Settle time for column switching (optimized for 4 nodes)
#define DISCARD_READS 1      // Reduced from 2: Discard reads after MUX switch for stabilization
#define FDC_CONVERSION_WAIT_MS 3  // Reduced from 10: Wait for FDC conversion after MUX switch

// Active nodes to scan (2x2 grid = 4 nodes)
#define NUM_ACTIVE_NODES 4
const int ACTIVE_NODES[NUM_ACTIVE_NODES][2] = {
  {0, 0},  // Row 0, Col 0
  {0, 1},  // Row 0, Col 1
  {1, 0},  // Row 1, Col 0
  {1, 1}   // Row 1, Col 1
};

FDC2214 capsense(FDC2214_I2C_ADDR_0);


// -------- MUX Control Functions --------
void setMuxPins(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
  digitalWrite(s2, (state >> 2) & 0x01);
}

void setupMuxPins() {
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);
  pinMode(MUX1_S2, OUTPUT);
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);
  pinMode(MUX2_S2, OUTPUT);
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


// -------- Setup --------
void setup() {
  Wire.begin();
  Serial.begin(115200);
  delay(300);

  Serial.println("\nFDC2214 8x8 Grid - Raw Capacitance Output");

  // Setup MUX pins
  setupMuxPins();
  
  // Initialize both muxes to state 0
  setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, 0);
  setMuxPins(MUX2_S0, MUX2_S1, MUX2_S2, 0);

  // Initialize FDC2214 with hardware settings from main_I.cpp
  // 0x01 = CH0 only, 0x00 = no autoscan, 0x01 = 1 MHz deglitch, true = internal oscillator
  bool ok = capsense.begin(
    0x01,   // CH0 only
    0x00,   // no autoscan
    0x01,   // 1 MHz deglitch (changed from 10MHz to 1MHz to reduce noise)
    true    // internal oscillator (changed from false to true)
  );
  Serial.println(ok ? "Sensor OK" : "Sensor FAIL");

  // Let FDC stabilize with initial mux state
  delay(200);
  
  Serial.println("Timestamp,Row_index,Column_index,Raw_Capacitance_pF");
}


// -------- Scan Node Function --------
unsigned long scanNode(int row, int col) {
  // Set MUX1 to current row
  setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, row);
  delayMicroseconds(ROW_SETTLE_US);
  
  // Set MUX2 to current column
  setMuxPins(MUX2_S0, MUX2_S1, MUX2_S2, col);
  delayMicroseconds(COL_SETTLE_US);
  
  // Wait for FDC oscillator to stabilize after MUX switch
  delay(FDC_CONVERSION_WAIT_MS);
  
  // Discard reads to allow FDC to fully stabilize
  for (int i = 0; i < DISCARD_READS; i++) {
    capsense.getReading28(0);
    delay(2);  // Reduced from 5: Small delay between discard reads
  }
  
  // Final stable reading
  unsigned long nodeValue = capsense.getReading28(0);
  
  return nodeValue;
}


// -------- Main Loop --------
void loop() {
  unsigned long timestamp = millis();
  
  // Scan only the 4 active nodes (much faster than 64 nodes)
  for (int i = 0; i < NUM_ACTIVE_NODES; i++) {
    int row = ACTIVE_NODES[i][0];
    int col = ACTIVE_NODES[i][1];
    
    // Get raw reading from FDC2214
    unsigned long reading = scanNode(row, col);
    
    // Convert to capacitance in pF
    double cap_pf = computeCap_pf(reading);
    
    // Output: Timestamp,Row_index,Column_index,Raw_Capacitance_pF
    Serial.print(timestamp);
    Serial.print(",");
    Serial.print(row);
    Serial.print(",");
    Serial.print(col);
    Serial.print(",");
    Serial.println(cap_pf, 3);  // 3 decimal places for capacitance
    
    // Reduced delay before next node (was 10ms, now 2ms)
    delay(2);
  }
  
  // Reduced delay between scans (was 50ms, now 5ms for faster updates)
  delay(5);
}
