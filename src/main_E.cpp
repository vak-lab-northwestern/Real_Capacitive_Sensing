#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

// Array size + timing
#define NUM_ROWS      8       // adjustable
#define NUM_COLS      8       // adjustable
#define ROW_SETTLE_US   8000  // longer settle for row switching (8ms)
#define COL_SETTLE_US   8000  // settle for column switching (8ms to allow oscillator to stabilize)
#define DISCARD_READS   2     // discard multiple reads after switching to allow FDC to stabilize
#define FDC_CONVERSION_WAIT_MS 10  // wait for FDC conversion cycle after MUX switch

// Row MUX (0–7)
#define ROW_S0 2
#define ROW_S1 3
#define ROW_S2 4

// Column MUX (0–7)
#define COL_S0 5
#define COL_S1 6
#define COL_S2 7

FDC2214 fdc(FDC2214_I2C_ADDR_0);

void setMux(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 1);
  digitalWrite(s1, (state >> 1) & 1);
  digitalWrite(s2, (state >> 2) & 1);
}

void selectRow(int r) {
  setMux(ROW_S0, ROW_S1, ROW_S2, r & 0x07);
}

void selectCol(int c) {
  setMux(COL_S0, COL_S1, COL_S2, c & 0x07);
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(115200);
  
  pinMode(ROW_S0, OUTPUT);
  pinMode(ROW_S1, OUTPUT);
  pinMode(ROW_S2, OUTPUT);
  pinMode(COL_S0, OUTPUT);
  pinMode(COL_S1, OUTPUT);
  pinMode(COL_S2, OUTPUT);
  
  selectRow(0);
  selectCol(0);
  
  // Configure FDC2214:
  // 0x01 = CH0 only (disable autoscan, single channel mode)
  // 0x00 = autoscan disabled (not needed for single channel)
  // 0x05 = deglitch at 10MHz (reduces noise)
  // false = external oscillator
  bool ok = fdc.begin(0x01, 0x00, 0x05, false);
  Serial.println(ok ? "FDC READY" : "FDC FAIL");
  
  // Let FDC stabilize with initial MUX state before starting measurements
  delay(200);
  
  Serial.println("Timestamp,Row_index,Column_index,Node_Value");
}

void loop() {
  for (int r = 0; r < NUM_ROWS; r++) {
    selectRow(r);
    delayMicroseconds(ROW_SETTLE_US);
    
    for (int c = 0; c < NUM_COLS; c++) {
      selectCol(c);
      delayMicroseconds(COL_SETTLE_US);
      
      // Wait for FDC oscillator to stabilize after MUX switch
      delay(FDC_CONVERSION_WAIT_MS);
      
      // Discard multiple reads to allow FDC to fully stabilize
      // This is critical - FDC needs time to adjust to new capacitance after MUX switch
      for (int i = 0; i < DISCARD_READS; i++) {
        fdc.getReading28(0);
        delay(5);  // Small delay between discard reads
      }
      
      // Final stable reading
      uint32_t valRow = fdc.getReading28(0);

      // Output: Timestamp, Row_index, Column_index, Node_Value
      unsigned long timestamp = millis();
      Serial.print(timestamp);
      Serial.print(",");
      Serial.print(r);
      Serial.print(",");
      Serial.print(c);
      Serial.print(",");
      Serial.println(valRow);
      
      // Small delay before next node
      delay(5);
    }
  }
  
  // Delay between full grid scans
  delay(10);
}