#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

// Create FDC2214 object at I2C address 0
FDC2214 capsense(FDC2214_I2C_ADDR_0);

// Constants
const float ref_clock = 40e6;        // 40 MHz reference clock
const float inductance = 180e-9;     // 180 nH inductor value
const float scale_factor = ref_clock / pow(2, 28);  // ~0.149 Hz per LSB

#define CHAN_COUNT 1  // Number of active sensor channels

void setup() {
  // Initialize I2C and Serial
  Wire.begin();
  Serial.begin(115200);
  Serial.println("\nFDC2x1x test");

  // Check for I2C device
  Serial.print("Scanning I2C... ");
  Wire.beginTransmission(FDC2214_I2C_ADDR_0);
  if (Wire.endTransmission() == 0) Serial.println("Device found!");
  else Serial.println("No response");

  // Initialize FDC2214 with 2 channels, 10 MHz deglitch filter, external oscillator
  bool capOk = capsense.begin(0x3, 0x4, 0x5, false);
  if (capOk) Serial.println("Sensor OK");
  else Serial.println("Sensor Fail");
}

void loop() {
  // Array to hold raw readings
  unsigned long capa[CHAN_COUNT];

  for (int i = 0; i < CHAN_COUNT; i++) {
    // Read 28-bit raw capacitance data from channel
    capa[i] = capsense.getReading28(i);
    uint32_t raw = capa[i];

    // Convert raw data to frequency
    float freq = raw * scale_factor;  // in Hz

    // Convert frequency to capacitance using LC formula
    float capacitance_F = 1.0 / (pow(2 * M_PI * freq, 2) * inductance);
    float capacitance_pF = capacitance_F * 1e12;  // convert to picofarads

    Serial.print(capacitance_pF);

  }

  delay(100); // Delay for stability
}
