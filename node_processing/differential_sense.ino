#include <Wire.h>
#include "FDC2214.h"

FDC2214 capsense(FDC2214_I2C_ADDR_0);  // ADDR pin to GND → 0x2A

// ------------------- MUX SELECT PINS -------------------
#define ROW_S0 3
#define ROW_S1 4
#define ROW_S2 5

#define COL_S0 7
#define COL_S1 8
#define COL_S2 9

// -------------------- TIMING CONSTANTS -----------------
#define ROW_SETTLE_US   5000     // settling after selecting a new row
#define COL_SETTLE_US    200     // settling after column switch
#define DISCARD_READS      1     // discard first read after every mux change

// --------------------------------------------------------
void setMux(int s0, int s1, int s2, int idx) {
  digitalWrite(s0, idx & 1);
  digitalWrite(s1, (idx >> 1) & 1);
  digitalWrite(s2, (idx >> 2) & 1);
}

void selectRow(int r) { setMux(ROW_S0, ROW_S1, ROW_S2, r); }
void selectCol(int c) { setMux(COL_S0, COL_S1, COL_S2, c); }

// --------------------------------------------------------
void setup() {
  Wire.begin();
  Serial.begin(115200);

  // MUX pin directions
  pinMode(ROW_S0, OUTPUT);
  pinMode(ROW_S1, OUTPUT);
  pinMode(ROW_S2, OUTPUT);

  pinMode(COL_S0, OUTPUT);
  pinMode(COL_S1, OUTPUT);
  pinMode(COL_S2, OUTPUT);

  bool ok = capsense.begin(
      0x02,   // CH1 only
      0x00,   // autoscan disabled
      0x05,   // deglitch 10MHz
      false   // using external oscillator
  );

  if (!ok)
    Serial.println("FDC2214 init FAIL");
  else
    Serial.println("FDC2214 READY (CH1 single-channel mode)");
}

// --------------------------------------------------------
void loop() {
  for (int r = 0; r < 8; r++) {
    selectRow(r);
    delayMicroseconds(ROW_SETTLE_US);

    for (int c = 0; c < 8; c++) {

      // Set column
      selectCol(c);
      delayMicroseconds(COL_SETTLE_US);

      // Discard first read (FDC always needs this after impedance changes)
      for (int i = 0; i < DISCARD_READS; i++)
        capsense.getReading28(1);

      // Actual reading from CH1
      uint32_t raw = capsense.getReading28(1);

      // CSV output: row,col,value
      Serial.print(r);
      Serial.print(",");
      Serial.print(c);
      Serial.print(",");
      Serial.println(raw);
    }
  }
}
