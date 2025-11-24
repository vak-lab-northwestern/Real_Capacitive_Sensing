#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include "FDC2214.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM, Differential)
  One 8:1 analog multiplexer connected to CH0 of FDC2214.
  Output format to Serial (one line per full scan):
  MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX1_4,MUX1_5,MUX1_6,MUX1_7\n
  where:
    MUX1_0-7 = FDC CH0 readings for MUX1 states 0–7
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
#define TOTAL_MUX_STATES   8   // 8:1 multiplexers
             // #define FDC_CHANNELS       2   // Using 2 FDC channels (CH0 and CH1)
#define FDC_CHANNELS       1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS     8  // 8 readings from MUX1
#define SETTLE_US 5500

// Calculated conversion time per channel: ~1.68ms
// For 2 channels: one full cycle = ~3.4ms
// Wait for 2 full cycles to ensure fresh data = ~7ms
// Add safety margin = 10ms total
#define FDC_CYCLE_WAIT_MS 10

FDC2214 fdc1(FDC2214_I2C_ADDR_0);

void setMuxPins(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
  digitalWrite(s2, (state >> 2) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  // Enable only CH0 and CH1 for faster conversion
  // 0x3 = binary 0011 = CH0 and CH1 enabled
  // 0x4 = autoscan sequence CH0->CH1
  bool ok = fdc.begin(0x3, 0x4, 0x5, false);   
  if (ok) Serial.print(name), Serial.println(" OK");
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
  
  Serial.println("Starting multiplexed capacitance scan (RAW)...");
  Serial.println("Format: MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX1_4,MUX1_5,MUX1_6,MUX1_7");
  
  // Let FDC stabilize with initial mux state
  delay(100);
}

void loop() {
  uint32_t readings[TOTAL_READINGS];
  
  //Update channel reading to match mux state

  // Scan through all 8 states for both multiplexers
  for (int muxState = 0; muxState < TOTAL_MUX_STATES; muxState++) {
    setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, muxState);
    setMuxPins(MUX2_S0, MUX2_S1, MUX2_S2, muxState);
    
    // Wait for mux to settle
    delayMicroseconds(SETTLE_US);
    
    // Wait for FDC to complete at least 2 full autoscan cycles
    // This ensures the readings reflect the new mux state
    delay(FDC_CYCLE_WAIT_MS);
    
    // The library's getReading28() already waits for data-ready flag
    readings[muxState] = fdc1.getReading28(0);
    // readings[muxState + 8] = fdc1.getReading28(1);
  }
  
  // Output all 8 readings as CSV
  for (int i = 0; i < TOTAL_READINGS; i++) {
    Serial.print(readings[i]);
    if (i < TOTAL_READINGS - 1) Serial.print(",");
  }
  Serial.println();
}