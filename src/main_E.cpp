#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

// Array size + timing
#define NUM_ROWS      8       // adjustable
#define NUM_COLS      8       // adjustable
#define ROW_SETTLE_US   5000  // longer settle for row switching
#define COL_SETTLE_US   150   // shorter settle for column switching
#define DISCARD_READ    1     // discard first read after switching

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
  
  bool ok = fdc.begin(0x3, 0x4, 0x5, false);
  Serial.println(ok ? "FDC READY" : "FDC FAIL");
  Serial.println("Row_index, Column_index, Node_Value");
}

void loop() {
  for (int r = 0; r < NUM_ROWS; r++) {
    selectRow(r);
    delayMicroseconds(ROW_SETTLE_US);
    
    for (int c = 0; c < NUM_COLS; c++) {
      selectCol(c);
      delayMicroseconds(COL_SETTLE_US);
      
      if (DISCARD_READ) { 
        fdc.getReading28(0);  
      }
      
      uint32_t valRow = fdc.getReading28(0); 

      // Output: Row_index, Column_index, Raw Cap Row, Raw Cap Column
      Serial.print(r);
      Serial.print(",");
      Serial.print(c);
      Serial.print(",");
      Serial.println(valRow);
      
      delay(10);
    }
  }
  
  delay(20);
}