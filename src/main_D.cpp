#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include <math.h>

#include <FDC2214s.h>
#include "cap.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM, Differential)
  Two 4:1 analog multiplexer connected to CH0 of FDC2214.
  Output format to Serial (one line per full scan):
  MUX1_0,MUX1_1,MUX1_2,MUX1_3,MUX1_4,MUX1_5,MUX1_6,MUX1_7\n
  where:
    MUX1_0-7 = FDC CH0 readings for MUX1 states 0–7
*/

// TEST 4x4
#define MUX_COL_S2 25
#define MUX_COL_S1 33
#define MUX_COL_S0 32

#define MUX_ROW_S2 26
#define MUX_ROW_S1 27
#define MUX_ROW_S0 14

// Constants
#define MUX_STATES        4 // 8 states for 3 select lines (8:1 mux)
#define FDC_CHANNELS       1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS     16
#define SCAN_PRINT 16

FDC2214 fdc1(FDC2214_I2C_ADDR_1);

void initFDC(FDC2214 &fdc, const char *name) {
  // Enable only CH0 and CH1 for faster conversion
  // 0x3 = binary 0011 = CH0 and CH1 enabled
  // 0x4 = autoscan sequence CH0->CH1
  // chanMask=0x01 (CH0), autoscanSeq=0 (no autoscan), deglitchValue=0 (default), intOsc=true
  bool ok = fdc.begin(0x01, 0x04, 0x05, true); 
  // if (ok) Serial.print(name), Serial.println(" OK");
  // else Serial.print(name), Serial.println(" FAIL");
}

void set_row(int s2, int s1, int s0, int state) {
  // 
  switch(state) {
    case 0:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, HIGH);
      break;
    case 1:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, LOW);
      digitalWrite(s0, HIGH);
      break;
    case 2:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, LOW);
      break;
    case 3:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
    case 4:
      digitalWrite(s2, LOW);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, LOW);
      break;
    case 5:
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, HIGH);
      break;
    case 6:
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
    case 7:
      digitalWrite(s2, LOW);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, HIGH);
      break;
    default:
      // Invalid state, default to 0
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
  }
}

void set_col(int s2, int s1, int s0, int state) {
  // 
  switch(state) {
    case 0:
      digitalWrite(s2, LOW);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, HIGH);
      break;
    case 1:
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
    case 2:
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, HIGH);
      break;
    case 3:
      digitalWrite(s2, LOW);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, LOW);
      break;
    case 4:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
    case 5:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, LOW);
      break;
    case 6:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, LOW);
      digitalWrite(s0, HIGH);
      break;
    case 7:
      digitalWrite(s2, HIGH);
      digitalWrite(s1, HIGH);
      digitalWrite(s0, HIGH);
      break;
    default:
      // Invalid state, default to 0
      digitalWrite(s2, LOW);
      digitalWrite(s1, LOW);
      digitalWrite(s0, LOW);
      break;
  }
}

void setupMuxPins() {
  pinMode(MUX_COL_S2, OUTPUT);
  pinMode(MUX_COL_S1, OUTPUT);
  pinMode(MUX_COL_S0, OUTPUT);
  pinMode(MUX_ROW_S2, OUTPUT);
  pinMode(MUX_ROW_S1, OUTPUT);
  pinMode(MUX_ROW_S0, OUTPUT);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(250000);

  setupMuxPins();
  set_col(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, 0);
  set_row(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, 0);

  initFDC(fdc1, "FDC");
  fdc1.enterSleepMode(); 
  delay(100);
}


// for graphing 16
void loop() {
  double current_scan[TOTAL_READINGS];
  // unsigned long t0 = micros();
  int idx = 0;
  
  for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
   set_row(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, mux1);

    for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
      set_col(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, mux2);
      
      fdc1.triggerSingleConversion(0);
      
      unsigned long raw = fdc1.getReading28(0);
      current_scan[idx++] = computeCap_pf(raw);
    }
 }
  
  // Serial.println();
  // Serial.print("# frame_us=");
  // Serial.println(micros() - t0);

  for (int i = 0; i < SCAN_PRINT; i++) {
    Serial.print(current_scan[i], 2); // 2 decimal places is faster to print than 4
    if (i < SCAN_PRINT - 1) {
      Serial.print(",");
    }
  }
  Serial.println();

}
