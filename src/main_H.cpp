#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include <math.h>

#include <FDC2214x.h>
#include "cap.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM, Differential)
  Two 4:1 analog multiplexer connected to CH0 of FDC2214.
  Output format to Serial (one line per full scan):
  MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX1_4,MUX1_5,MUX1_6,MUX1_7\n
  where:
    MUX1_0-7 = FDC CH0 readings for MUX1 states 0–7
*/

// MUX pin mapping 
#define MUX2_C 2 // MSB
#define MUX2_B 3 //    
#define MUX2_A 4 // LSB

#define MUX1_C 5 // MSB
#define MUX1_B 6 //  
#define MUX1_A 7 // LSB

// Constants
#define MUX_STATES        8   // 8 states for 3 select lines (8:1 mux)
#define FDC_CHANNELS       1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS     64
#define SCAN_PRINT 64

FDC2214 fdc1(FDC2214_I2C_ADDR_0);

void setMuxPins(int s0, int s1, int s2, int state) {
  digitalWrite(s0, (state >> 2) & 0x01); 
  digitalWrite(s1, (state >> 1) & 0x01); 
  digitalWrite(s2, (state >> 0) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  // Enable only CH0 and CH1 for faster conversion
  // 0x3 = binary 0011 = CH0 and CH1 enabled
  // 0x4 = autoscan sequence CH0->CH1

  bool ok = fdc.begin(0x01, 0x04, 0x05, true); // chanMask=0x01 (CH0), autoscanSeq=0 (no autoscan), deglitchValue=0 (default), intOsc=true

  // if (ok) Serial.print(name), Serial.println(" OK");
  // else Serial.print(name), Serial.println(" FAIL");
}

void setupMuxPins() {
  pinMode(MUX1_C, OUTPUT);
  pinMode(MUX1_B, OUTPUT);
  pinMode(MUX1_A, OUTPUT);
  pinMode(MUX2_C, OUTPUT);
  pinMode(MUX2_B, OUTPUT);
  pinMode(MUX2_A, OUTPUT);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(250000);

  setupMuxPins();
  
  // Initialize both muxes to state 0
  setMuxPins(MUX1_C, MUX1_B, MUX1_A, 0);
  setMuxPins(MUX2_C, MUX2_B, MUX2_A, 0);
  
  initFDC(fdc1, "FDC");

  fdc1.enterSleepMode(); 
  
  // Serial.println("Starting multiplexed capacitance scan (RAW)...");
  
  // Let FDC stabilize with initial mux state
  delay(100);
}


// for graphing 16
void loop() {
  double current_scan[TOTAL_READINGS];
  // unsigned long t0 = micros();
  int idx = 0;
  
  for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
    setMuxPins(MUX1_C, MUX1_B, MUX1_A, mux1);

    for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
      setMuxPins(MUX2_C, MUX2_B, MUX2_A, mux2);
      
      
      fdc1.triggerSingleConversion(0);
      
      unsigned long raw = fdc1.getReading28(0);
      current_scan[idx++] = computeCap_pf(raw);
    }
  }
  
  // Serial.println();
  // Serial.print("# frame_us=");
  // Serial.println(micros() - t0);

  // Print all 64 values (one full frame)
  for (int i = 0; i < SCAN_PRINT; i++) {
    Serial.print(current_scan[i], 2); // 2 decimal places is faster to print than 4
    if (i < SCAN_PRINT - 1) {
      Serial.print(",");
    }
  }
  Serial.println();

}
