#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

/*
  Dual FDC2214 Continuous Time-Division Multiplexing (TDM)
  Each FDC2214 uses its own 4:1 analog multiplexer.

  Output format to Serial (one line per full scan):
  CH0,CH1,CH2,CH3,CH4,CH5,CH6,CH7\n
  where:
    CH0–CH3 = FDC1 readings for MUX states 0–3
    CH4–CH7 = FDC2 readings for MUX states 0–3
*/

// MUX pin mapping
#define MUX1_S0 2   // FDC1 select bit 0 (LSB)
#define MUX1_S1 3   // FDC1 select bit 1 (MSB)
#define MUX2_S0 4   // FDC2 select bit 0 (LSB)
#define MUX2_S1 5   // FDC2 select bit 1 (MSB)

// Constants
#define TOTAL_MUX_CHANNELS 4
#define SETTLE_MS 5         // allow short settling time after switching
#define BETWEEN_CHIP_US 300 // small gap between reading chip1 and chip2
#define SWITCH_INTERVAL 0   // no extra ms needed; pacing handled by SETTLE_MS

// FDC2214 Objects
FDC2214 fdc1(FDC2214_I2C_ADDR_0); // Address 0x2A (ADDR pin LOW)
FDC2214 fdc2(FDC2214_I2C_ADDR_1); // Address 0x2B (ADDR pin HIGH)

// Helper Functions
void setMuxPins(int s0, int s1, int state) {
  digitalWrite(s0, state & 0x01);
  digitalWrite(s1, (state >> 1) & 0x01);
}

void initFDC(FDC2214 &fdc, const char *name) {
  bool ok = fdc.begin(0x3, 0x4, 0x5, false);
  if (ok) Serial.print(name), Serial.println(" OK");
  else Serial.print(name), Serial.println(" FAIL");
}

void setup() {
  Wire.begin();
  Serial.begin(9600);

  // Configure MUX control pins
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);

  // Initialize MUX to channel 0
  setMuxPins(MUX1_S0, MUX1_S1, 0);
  setMuxPins(MUX2_S0, MUX2_S1, 0);

  // Initialize both FDCs
  initFDC(fdc1, "FDC1");
  initFDC(fdc2, "FDC2");

  Serial.println("Starting multiplexed capacitance scan (RAW)...");
  delay(500);
}

// Main Loop
void loop() {
  unsigned long readings[8];

  for (int muxState = 0; muxState < TOTAL_MUX_CHANNELS; muxState++) {
    // Set both muxes
    setMuxPins(MUX1_S0, MUX1_S1, muxState);
    setMuxPins(MUX2_S0, MUX2_S1, muxState);

    // Wait for switch to settle
    delay(SETTLE_MS);

    // Read FDC1 (raw)
    readings[muxState] = fdc1.getReading28(0);

    // small gap between chips
    delayMicroseconds(BETWEEN_CHIP_US);

    // Read FDC2 (raw)
    readings[muxState + 4] = fdc2.getReading28(0);
  }

  // Print CSV
  for (int i = 0; i < 8; i++) {
    Serial.print(readings[i]);
    if (i < 7) Serial.print(",");
  }
  Serial.println();
}
