#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>

#include "FDC2214.h"

/*
  FDC2214 Continuous Time-Division Multiplexing (TDM)
  Each FDC2214 uses its own 8:1 analog multiplexer.

  Output format to Serial (one line per full scan):
  CH0,CH1,CH2,CH3,CH4,CH5,CH6,CH7\n
  where:
    CH0–CH3 = FDC1 readings for MUX states 0–7  
*/

// MUX pin mapping
#define MUX1_S0 3   // FDC1 select bit 0 (LSB)
#define MUX1_S1 4   // FDC1 select bit 1 
#define MUX1_S2 5   // FDC1 select bit 2 (MSB)
    
// Constants
#define TOTAL_MUX_STATES   8
#define FDC_CHANNELS       4
#define TOTAL_READINGS     (TOTAL_MUX_STATES * FDC_CHANNELS)
#define SETTLE_US 5500       

 FDC2214 fdc1(FDC2214_I2C_ADDR_0); // Address 0x2B (ADDR pin HIGH)

void setMuxPins(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
  digitalWrite(s2, (state >> 2) & 0x01);
}


// CSV recording 
void csv_recording() {
  
}

void initFDC(FDC2214 &fdc, const char *name) {
  bool ok = fdc.begin(0xF, 0x6, 0x5, false); 
  if (ok) Serial.print(name), Serial.println(" OK");
  else Serial.print(name), Serial.println(" FAIL");
}

// void printFDC(FDC2214& fdc) {
//   int fdc_chan = 4;
//   for (int i = 0; i < fdc_chan; i++) {
//     Serial.print(fdc.getReading28(i));
//     Serial.print(",");
//   } 
//   Serial.println();
// }

void setup() {
  Wire.begin();
  Wire.setClock(400000); // increasing i2c clock speed
  Serial.begin(115200);

  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT); 
  pinMode(MUX1_S2, OUTPUT);

  setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, 0);

  initFDC(fdc1, "FDC");

  Serial.println("Starting multiplexed capacitance scan (RAW)...");
  delay(100);
}

void loop() {
  uint32_t readings[TOTAL_READINGS];
  int idx = 0;

  for (int muxState = 0; muxState < TOTAL_MUX_STATES; muxState++) {
    setMuxPins(MUX1_S0, MUX1_S1, MUX1_S2, muxState);
    delayMicroseconds(SETTLE_US);

    for (int ch = 0; ch < FDC_CHANNELS; ch++) {
      readings[idx++] = fdc1.getReading28(ch);
    }
  }

  for (int i = 0; i < TOTAL_READINGS; i++) {
    Serial.print(readings[i]);
    if (i < TOTAL_READINGS - 1) Serial.print(",");
  }
  Serial.println();
}
