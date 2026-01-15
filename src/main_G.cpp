#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include "FDC2214.h"
#include <math.h>
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
#define MUX1_S1 3 // MSB

#define MUX2_S0 5 // LSB
#define MUX2_S1 6 // MSB

// Constants
#define MUX_STATES        4   // 4 states for 2 select lines (4:1 mux)
#define FDC_CHANNELS       1   // Using 1 FDC channel (CH0)
#define TOTAL_READINGS     16  // 8 readings from MUX1
#define SETTLE_US 5500

// Calculated conversion time per channel: ~1.68ms
// For 2 channels: one full cycle = ~3.4ms
// Wait for 2 full cycles to ensure fresh data = ~7ms
// Add safety margin = 10ms total
#define FDC_CYCLE_WAIT_MS 100

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
  if (ok) Serial.print(name), Serial.println(" OK");
  else Serial.print(name), Serial.println(" FAIL");
}

void setupMuxPins() {
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);
}

double computeCap_pf(unsigned long reading) {
  const double fref = 40000000.0;  // 40 MHz internal reference
  const double L = 18e-6;          // 18 uH inductor
  const double Cboard = 33e-12;    // 33 pF fixed board capacitor
  const double Cpar = 3e-12;       // parasitics (adjust if needed)

  // Convert raw code → frequency
  double fs = (fref * (double)reading) / 268435456.0; // 2^28

  // LC resonance equation → total capacitance
  double Ctotal = 1.0 / ( (2.0 * M_PI * fs) * (2.0 * M_PI * fs) * L );

  // Remove board + parasitic capacitance
  double Csensor = Ctotal - (Cboard + Cpar);

  return Csensor * 1e12; // convert to picofarads
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
  
  Serial.println("Starting multiplexed capacitance scan (RAW)...");
  
  // Let FDC stabilize with initial mux state
  delay(100);
}

void loop() {
  uint32_t readings[TOTAL_READINGS];
  int index = 0;

  for (int mux1 = 0; mux1 < MUX_STATES; mux1++) {
    setMuxPins(MUX1_S0, MUX1_S1, mux1);

    for (int mux2 = 0; mux2 < MUX_STATES; mux2++) {
      setMuxPins(MUX2_S0, MUX2_S1, mux2);

      //delayMicroseconds(SETTLE_US);
      //delay(FDC_CYCLE_WAIT_MS);
      unsigned long fre = fdc1.getReading28(0);
      readings[index++] = computeCap_pf(fre);
    }
  }

  for (int i = 0; i < TOTAL_READINGS; i++) {
    Serial.print(readings[i]);
    if (i < TOTAL_READINGS - 1) Serial.print(",");
  }
  Serial.println();
}