#include <Wire.h>
#include "FDC2214.h"

// ===== Two MUX pin labels (distinct ICs) =====
const uint8_t COL_MUX_A = 5;
const uint8_t COL_MUX_B = 6;
const uint8_t COL_MUX_C = 7;

const uint8_t ROW_MUX_A = 2;
const uint8_t ROW_MUX_B = 3;
const uint8_t ROW_MUX_C = 4;

// Create FDC instance at default addr (0x2A or 0x2B allowed)
FDC2214 fdc(FDC2214_I2C_ADDR_0);

// Chip operates fine at 5V since 5V is within parametric rating.
// The mux pins described in the datasheet show 5V mode explicitly works. :contentReference[oaicite:1]{index=1}

// set COLUMN mux  (0–7 generalizable)
void setColumn(uint8_t col) {
    col &= 0x07;  // clamp 3-bit (0–7)
    digitalWrite(COL_MUX_A,  col        & 0x01);
    digitalWrite(COL_MUX_B, (col >> 1)  & 0x01);
    digitalWrite(COL_MUX_C, (col >> 2)  & 0x01);
}

// set ROW mux (0–7 generalizable, but grid only uses 0–3)
void setRow(uint8_t row) {
    row &= 0x07;
    digitalWrite(ROW_MUX_A,  row        & 0x01);
    digitalWrite(ROW_MUX_B, (row >> 1)  & 0x01);
    digitalWrite(ROW_MUX_C, (row >> 2)  & 0x01);
}

// read a single grid cell by fixing row + selecting col (CH0 only)
unsigned long readGridCell(uint8_t row, uint8_t col) {
    setRow(row); // fixes which row line is connected
    setColumn(col);  // connects column lines into CH0 path
    // delayMicroseconds(5000); // 5ms settle more robust for cap
    delay(50);  // need minimum 20ms delay for cap to settle well
                // smaller delay leads to worse signal stability
    return fdc.getReading28(0);
}

void setup() {
    Serial.begin(115200);
    Wire.begin();

    // Init digital pins for mux control
    pinMode(COL_MUX_A, OUTPUT);
    pinMode(COL_MUX_B, OUTPUT);
    pinMode(COL_MUX_C, OUTPUT);

    pinMode(ROW_MUX_A, OUTPUT);
    pinMode(ROW_MUX_B, OUTPUT);
    pinMode(ROW_MUX_C, OUTPUT);

    // Initialize FDC2214 with CH0 only enabled (mask 0x01)
    // 0x01 - manual mode, 0 - disable autoscan, 0 - no deglitch filtering, true - internal oscillator
    if (!fdc.begin(0x01, 0, 0, true)) {  
        Serial.println("FDC2214 not detected. Check I2C.");
        while (1);
    }

    Serial.println("FDC2214 Ready.");
}

void loop() {
    // Serial.println("\n--- 4x4 GRID SCAN (single CH0) ---");
    unsigned long timestamp = millis();
    // Scan up to 8 generalized channels, stop at 4 for grid
    for (uint8_t row = 0; row < 2; row++) {
        for (uint8_t col = 0; col < 2; col++) {
            unsigned long val = readGridCell(row, col);
            Serial.print(timestamp); Serial.print(" , ");
            Serial.print("Row "); Serial.print(row);
            Serial.print(", Col "); Serial.print(col);
            Serial.print(" : "); 
            Serial.println(val);  // not converted to pF, 28 bits wide, no decimal
        }
        // if (col >= 4) break; // grid has 4 columns, ignore rest
    }

    // unsigned long val = readGridCell(0, 0);
    // Serial.println(val);

    // unsigned long val = readGridCell(heldRow, 0);
    // // Serial.print("Row "); Serial.print(heldRow);
    // // Serial.print(", Col "); Serial.print(0);
    // // Serial.print(" : "); 
    // Serial.println(val);

    // delay(25);
}
