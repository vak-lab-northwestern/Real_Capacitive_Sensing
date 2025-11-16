#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

#define NUM_ROWS 8
#define NUM_COLS 8

#define ROW_SETTLE_US 4000
#define COL_SETTLE_US 200
#define DISCARD_DELAY_MS 4

#define ROW_S0 3
#define ROW_S1 4
#define ROW_S2 5

#define COL_S0 7
#define COL_S1 8
#define COL_S2 9

FDC2214 fdc(FDC2214_I2C_ADDR_0);

void setMux(int s0, int s1, int s2, int state) {
  digitalWrite(s0, state & 1);
  digitalWrite(s1, (state >> 1) & 1);
  digitalWrite(s2, (state >> 2) & 1);
}

void selectRow(int r) { setMux(ROW_S0, ROW_S1, ROW_S2, r & 0x07); }
void selectCol(int c) { setMux(COL_S0, COL_S1, COL_S2, c & 0x07); }

void discardfirstline() {
  fdc.getReading28(0);
  delay(DISCARD_DELAY_MS);
  fdc.getReading28(1);
  delay(DISCARD_DELAY_MS);
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);

  pinMode(ROW_S0, OUTPUT);
  pinMode(ROW_S1, OUTPUT);
  pinMode(ROW_S2, OUTPUT);
  pinMode(COL_S0, OUTPUT);
  pinMode(COL_S1, OUTPUT);
  pinMode(COL_S2, OUTPUT);

  selectRow(0);
  selectCol(0);

  bool ok = fdc.begin(0xF, 0x6, 0x5, false);
  Serial.println(ok ? "FDC READY" : "FDC FAIL");

  Serial.println("ROW0,ROW1,ROW2,ROW3,ROW4,ROW5,ROW6,ROW7,COL0,COL1,COL2,COL3,COL4,COL5,COL6,COL7");
}

void loop() {
  uint32_t rows[NUM_ROWS];
  uint32_t cols[NUM_COLS];

  for (int r = 0; r < NUM_ROWS; r++) {
    selectRow(r);
    selectCol(r);
    delayMicroseconds(ROW_SETTLE_US);
    discardfirstline();
    rows[r] = fdc.getReading28(0);
  }

  for (int c = 0; c < NUM_COLS; c++) {
    selectRow(c);
    selectCol(c);
    delayMicroseconds(COL_SETTLE_US);
    discardfirstline();
    cols[c] = fdc.getReading28(1);
  }

  for (int i = 0; i < NUM_ROWS; i++) {
    Serial.print(rows[i]);
    Serial.print(",");
  }

  for (int i = 0; i < NUM_COLS; i++) {
    Serial.print(cols[i]);
    if (i < NUM_COLS - 1) Serial.print(",");
  }

  Serial.println();
}
