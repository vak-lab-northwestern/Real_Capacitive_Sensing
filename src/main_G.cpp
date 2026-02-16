#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include <math.h>

#include "FDC2214.h"
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
#define MUX2_S0 2 // LSB   
#define MUX2_S1 3 // MSB

#define MUX1_S0 5 // LSB
#define MUX1_S1 6 // MSB

// Constants
#define MUX_STATES        4   // 4 states for 2 select lines (4:1 mux)
#define FDC_CHANNELS       1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS     16  

FDC2214 fdc1(FDC2214_I2C_ADDR_0);

void setMuxPins(int s0, int s1, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  // Enable only CH0 and CH1 for faster conversion
  // 0x3 = binary 0011 = CH0 and CH1 enabled
  // 0x4 = autoscan sequence CH0->CH1
  bool ok = fdc.begin(0x1, 0x4, 0x5, true);   
  // if (ok) Serial.print(name), Serial.println(" OK");
  // else Serial.print(name), Serial.println(" FAIL");
}

void setupMuxPins() {
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(115200);

  setupMuxPins();
  
  // Initialize both muxes to state 0
  setMuxPins(MUX1_S0, MUX1_S1, 0);
  setMuxPins(MUX2_S0, MUX2_S1, 0);
  
  initFDC(fdc1, "FDC");
  
  // Serial.println("Starting multiplexed capacitance scan (RAW)...");
  
  // Let FDC stabilize with initial mux state
  delay(100);
}

// void loop() {
//   for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
//     setMuxPins(MUX1_S0, MUX1_S1, mux1);

//     for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
//       setMuxPins(MUX2_S0, MUX2_S1, mux2);
//       unsigned long fre = fdc1.getReading28(0);
//       int val = computeCap_pf(fre);

//       char buf[64];
//       snprintf(buf, sizeof(buf),
//          "%lu, Row %d, Col %d : %d",
//          millis(), mux1, mux2, val);
//       Serial.println(buf);
//       delay(50);
//     }
//   }
// }


// for graphing 16
void loop() {
  double current_scan[16];
  int idx = 0;

  for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
    setMuxPins(MUX1_S0, MUX1_S1, mux1);
    for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
      setMuxPins(MUX2_S0, MUX2_S1, mux2);
      
      delay(15); // Give the FDC time to settle after MUX switch
      
      unsigned long raw = fdc1.getReading28(0);
      current_scan[idx++] = computeCap_pf(raw);
    }
  }

  // Print all 16 values on one line for the Python script
  for (int i = 0; i < 16; i++) {
    Serial.print(current_scan[i], 4); // Print with 4 decimal places
    if (i < 15) {
      Serial.print(","); // Only add comma between values
    }
  }
  Serial.println(); //
}