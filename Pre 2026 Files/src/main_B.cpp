#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include <math.h>

#include <FDC2214s.h>
#include "cap.h"

// TEST 2x2 Pin Mapping
#define MUX2_A1 27
#define MUX2_A0 25

#define MUX1_A1 14
#define MUX1_A0 32

// Constants
#define MUX_STATES        2   // 2 states for 2 select lines (2x2 matrix)
#define FDC_CHANNELS      1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS    4   // Max total readings for a full matrix scan
#define SCAN_PRINT        2   // When testing ONE mux, we only print 2 channels

FDC2214 fdc1(FDC2214_I2C_ADDR_1);

// ==========================================
// TEST CONFIGURATION
// ==========================================
const bool TEST_MUX1_ONLY = false;   // Set to true to isolate MUX1 (MUX2 frozen at state 0)
const bool TEST_MUX2_ONLY = false;  // Set to true to isolate MUX2 (MUX1 frozen at state 0)
// Note: If both are false, it defaults back to your original 2x2 matrix scan.
// ==========================================

void setMuxPins(int s1, int s0, int state) {
  digitalWrite(s1, (state >> 1) & 0x01); 
  digitalWrite(s0, (state >> 0) & 0x01); 
}

void initFDC(FDC2214 &fdc, const char *name) {
  bool ok = fdc.begin(0x01, 0x04, 0x05, true); 
}

void setupMuxPins() {
  pinMode(MUX1_A1, OUTPUT);
  pinMode(MUX1_A0, OUTPUT);
  pinMode(MUX2_A1, OUTPUT);
  pinMode(MUX2_A0, OUTPUT);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(250000);

  setupMuxPins();
  
  // Initialize both muxes to state 0
  setMuxPins(MUX1_A1, MUX1_A0, 0);
  setMuxPins(MUX2_A1, MUX2_A0, 0);

  initFDC(fdc1, "FDC");
  fdc1.enterSleepMode(); 
  
  delay(100);
}

void loop() {
  double current_scan[TOTAL_READINGS];
  int idx = 0;
  int current_scan_print = SCAN_PRINT;

  // -------------------------------------------------------------
  // MODE 1: TEST MUX1 ONLY
  // -------------------------------------------------------------
  if (TEST_MUX1_ONLY) {
    current_scan_print = MUX_STATES; // We only expect 2 prints
    setMuxPins(MUX2_A1, MUX2_A0, 0); // Keep MUX2 frozen at channel 0
    
    for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
      setMuxPins(MUX1_A1, MUX1_A0, mux1); // Cycle MUX1
      
      fdc1.triggerSingleConversion(0);
      unsigned long raw = fdc1.getReading28(0);
      current_scan[idx++] = computeCap_pf(raw);
    }
  }
  
  // -------------------------------------------------------------
  // MODE 2: TEST MUX2 ONLY
  // -------------------------------------------------------------
  else if (TEST_MUX2_ONLY) {
    current_scan_print = MUX_STATES; // We only expect 2 prints
    setMuxPins(MUX1_A1, MUX1_A0, 0); // Keep MUX1 frozen at channel 0
    
    for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
      setMuxPins(MUX2_A1, MUX2_A0, mux2); // Cycle MUX2
      
      fdc1.triggerSingleConversion(0);
      unsigned long raw = fdc1.getReading28(0);
      current_scan[idx++] = computeCap_pf(raw);
    }
  }
  
  // -------------------------------------------------------------
  // MODE 3: DEFAULT 2x2 SCAN (Original code behavior)
  // -------------------------------------------------------------
  else {
    current_scan_print = TOTAL_READINGS; // Expecting 4 prints
    for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
      setMuxPins(MUX1_A1, MUX1_A0, mux1);

      for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
        setMuxPins(MUX2_A1, MUX2_A0, mux2);
        
        fdc1.triggerSingleConversion(0);
        unsigned long raw = fdc1.getReading28(0);
        current_scan[idx++] = computeCap_pf(raw);
      }
    }
  }
  
  // Print values dynamically depending on which test mode is active
  for (int i = 0; i < current_scan_print; i++) {
    Serial.print(current_scan[i], 2); 
    if (i < current_scan_print - 1) {
      Serial.print(",");
    }
  }
  Serial.println();
}