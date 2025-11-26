#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM, Differential)
  Two 8:1 analog multiplexers (MUX1 for rows, MUX2 for columns) connected to FDC2214 CH0.
  Output format to Serial (one line per node):
  Timestamp,Row_index,Column_index,Node_Value
  where:
    Row_index = MUX1 state (0-7)
    Column_index = MUX2 state (0-7)
    Node_Value = FDC CH0 raw 28-bit frequency reading (NOT capacitance in pF)
    
  Note: Node_Value is a frequency count from the FDC2214. Lower values = higher capacitance.
        To convert to capacitance: freq = Node_Value * (40MHz / 2^28)
                                   C = 1 / ((2π * freq)^2 * L)
        Typical values: 10-500pF sensors produce readings in range 100,000 - 15,000,000
*/

// MUX pin mapping (3 select lines for 8:1 mux)
// SN74HC4051 follows this format: C B A == S2 S1 S0
#define MUX1_S0 2 // LSB   
#define MUX1_S1 3
#define MUX1_S2 4 // MSB
#define MUX2_S0 5 // LSB
#define MUX2_S1 6
#define MUX2_S2 7 // MSB

// Constants
#define TOTAL_MUX_STATES 8   // 8:1 multiplexers (8 rows, 8 columns)
#define ROW_SETTLE_US 8000   // Longer settle for row switching (8ms) - matching main_E.cpp
#define COL_SETTLE_US 8000   // Settle for column switching (8ms to allow oscillator to stabilize)
#define DISCARD_READS 2      // Discard multiple reads after switching to allow FDC to stabilize
#define FDC_CONVERSION_WAIT_MS 10  // Wait for FDC conversion cycle after MUX switch
#define DEBUG_MODE 0         // Set to 1 to enable debug output

FDC2214 fdc1(FDC2214_I2C_ADDR_0);

void setMuxPins(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
  digitalWrite(s2, (state >> 2) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  // Configure FDC2214:
  // 0x01 = CH0 only (disable autoscan, single channel mode)
  // 0x00 = autoscan disabled (not needed for single channel)
  // 0x05 = deglitch at 10MHz (reduces noise)
  // false = external oscillator
  bool ok = fdc.begin(0x3, 0x4, 0x5, false);   
  if (ok) Serial.print(name), Serial.println(" READY");
  else Serial.print(name), Serial.println(" FAIL");
}

void setupMuxPins() {
    pinMode(MUX1_S0, OUTPUT);
    pinMode(MUX1_S1, OUTPUT);
    pinMode(MUX1_S2, OUTPUT);
    pinMode(MUX2_S0, OUTPUT);
    pinMode(MUX2_S1, OUTPUT);
    pinMode(MUX2_S2, OUTPUT);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(115200);

  setupMuxPins();
  
  // Initialize both muxes to state 0
  setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, 0);
  setMuxPins(MUX2_S0, MUX2_S1, MUX2_S2, 0);
  
  initFDC(fdc1, "FDC");
  
  // Let FDC stabilize with initial mux state
  delay(200);
  
  Serial.println("Timestamp,Row_index,Column_index,Node_Value");
}

void loop() {
  // Scan through all row states
  for (int row = 0; row < TOTAL_MUX_STATES; row++) {
    // Set MUX1 to current row
    setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, row);
    delayMicroseconds(ROW_SETTLE_US);
    
    if (DEBUG_MODE) {
      Serial.print("#DEBUG: Row="); Serial.println(row);
    }
    
    // Scan through all column states
    for (int col = 0; col < TOTAL_MUX_STATES; col++) {
      // Set MUX2 to current column
      setMuxPins(MUX2_S0, MUX2_S1, MUX2_S2, col);
      delayMicroseconds(COL_SETTLE_US);
      
      // Wait for FDC oscillator to stabilize after MUX switch
      delay(FDC_CONVERSION_WAIT_MS);
      
      // Discard multiple reads to allow FDC to fully stabilize
      // This is critical - FDC needs time to adjust to new capacitance after MUX switch
      for (int i = 0; i < DISCARD_READS; i++) {
        uint32_t discardVal = fdc1.getReading28(0);
        if (DEBUG_MODE && i == 0) {
          Serial.print("#DEBUG: R"); Serial.print(row);
          Serial.print(",C"); Serial.print(col);
          Serial.print(" discard[0]="); Serial.println(discardVal);
        }
        delay(5);  // Small delay between discard reads
      }
      
      // Final stable reading
      uint32_t nodeValue = fdc1.getReading28(0);
      
      if (DEBUG_MODE) {
        Serial.print("#DEBUG: R"); Serial.print(row);
        Serial.print(",C"); Serial.print(col);
        Serial.print(" final="); Serial.println(nodeValue);
      }
      
      // Output: Timestamp, Row_index, Column_index, Node_Value
      unsigned long timestamp = millis();
      Serial.print(timestamp);
      Serial.print(",");
      Serial.print(row);
      Serial.print(",");
      Serial.print(col);
      Serial.print(",");
      Serial.println(nodeValue);
      
      // Small delay before next node
      delay(50);
    }
  }
  
  // Delay between full grid scans
  delay(100);
}