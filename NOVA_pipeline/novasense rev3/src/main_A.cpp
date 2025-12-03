#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

// Create sensor object at default I2C address
FDC2214 fdc(FDC2214_I2C_ADDR_0);

const uint8_t COL_MUX_A = 7;
const uint8_t COL_MUX_B = 6;
const uint8_t COL_MUX_C = 5;

const uint8_t ROW_MUX_A = 2;
const uint8_t ROW_MUX_B = 3;
const uint8_t ROW_MUX_C = 4;

void setup() {
  Serial.begin(115200);

  // Start FDC2214 with:
  // all channels enabled (0x0F), autoscan=0, deglitch=1MHz, internal osc=true
  if (!fdc.begin(0x01, 0, 1, true)) {
    Serial.println("FDC2214 NOT detected. Check wiring!");
    while (1);
  }

  Serial.println("FDC2214 Ready!");
}

void loop() {
  // Read all 4 channels (autoscan)
  unsigned long ch0 = fdc.getReading28(0);
  // unsigned long ch1 = fdc.getReading28(1);
  // unsigned long ch2 = fdc.getReading28(2);
  // unsigned long ch3 = fdc.getReading28(3);

  Serial.println(ch0);
  // Serial.print(" | CH1: "); Serial.print(ch1);
  // Serial.print(" | CH2: "); Serial.print(ch2);
  // Serial.print(" | CH3: "); Serial.println(ch3);

  delay(200);
}
