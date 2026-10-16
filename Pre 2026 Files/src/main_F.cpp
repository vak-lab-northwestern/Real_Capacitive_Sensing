#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include "FDC2214.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM)
  Two 4:1 analog multiplexers connected to CH0 and CH1 of FDC2214.
  Output format to Serial (one line per full scan):
  MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX2_0,MUX2_1,MUX2_2,MUX2_3\n
*/

// MUX pin mapping
#define MUX1_S0 2   
#define MUX1_S1 3    
#define MUX2_S0 4    
#define MUX2_S1 5

// Constants
#define TOTAL_MUX_STATES   4
#define FDC_CHANNELS       2
#define TOTAL_READINGS     8
#define SETTLE_US 5500

// Calculated conversion time per channel: ~1.68ms
// For 2 channels: one full cycle = ~3.4ms
// Wait for 2 full cycles to ensure fresh data = ~7ms
// Add safety margin = 10ms total
#define FDC_CYCLE_WAIT_MS 75

FDC2214 fdc1(FDC2214_I2C_ADDR_1);

void setMuxPins(int s0, int s1, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  // Enable only CH0 and CH1 for faster conversion
  // 0x3 = binary 0011 = CH0 and CH1 enabled
  // 0x1 = autoscan sequence CH0->CH1
  bool ok = fdc.begin(0x3, 0x4, 0x5, false);   
  if (ok) Serial.print(name), Serial.println(" OK");
  else Serial.print(name), Serial.println(" FAIL");
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(115200);
  
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);   
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);
  
  setMuxPins(MUX1_S0, MUX1_S1, 0);
  setMuxPins(MUX2_S0, MUX2_S1, 0);
  
  initFDC(fdc1, "FDC");
  
  Serial.println("Starting multiplexed capacitance scan (RAW)...");
  Serial.println("Format: MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX2_0,MUX2_1,MUX2_2,MUX2_3");
  
  // Let FDC stabilize with initial mux state
  delay(100);
}

void loop() {
  uint32_t readings[TOTAL_READINGS];
  
  for (int muxState = 0; muxState < TOTAL_MUX_STATES; muxState++) {
    // Set both muxes to the same state
    setMuxPins(MUX1_S0, MUX1_S1, muxState);
    setMuxPins(MUX2_S0, MUX2_S1, muxState);
    
    // Wait for mux to settle
    delayMicroseconds(SETTLE_US);
    
    // Wait for FDC to complete at least 2 full autoscan cycles
    // This ensures the readings reflect the new mux state
    delay(FDC_CYCLE_WAIT_MS);
    
    // The library's getReading28() already waits for data-ready flag
    // So these calls will block until fresh data is available
    readings[muxState] = fdc1.getReading28(0);      // MUX1
    readings[muxState + 4] = fdc1.getReading28(1);  // MUX2
  }
  
  // Output all 8 readings as CSV
  for (int i = 0; i < TOTAL_READINGS; i++) {
    Serial.print(readings[i]);
    if (i < TOTAL_READINGS - 1) Serial.print(",");
  }
  Serial.println();
}