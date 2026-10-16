// 8x8 capacitance grid: FDC2214 (FDC2214x.h driver) + two 8:1 muxes on CH0.
//
// Plain-text output, readable in the serial monitor. One line per cell, sent as soon
// as that cell is read:
//     <row>,<col>,<milli-pF>        e.g.  3,5,299140   (= 299.140 pF)
// and one line after every full 8x8 scan:
//     #frame_us=<microseconds the scan took>
#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <FDC2214x.h>
#include "cap.h"            // provides computeCap_pf(raw)

constexpr unsigned long SERIAL_BAUD = 115200;   // must match --baud on the Python script

#define MUX_COL_S2 18
#define MUX_COL_S1 5
#define MUX_COL_S0 17
#define MUX_ROW_S2 19
#define MUX_ROW_S1 16
#define MUX_ROW_S0 4

constexpr int ROWS = 8;   // set both to 4 for the 4x4 test board
constexpr int COLS = 8;

// SN74LV4051A: select pins S0=A (LSB), S1=B, S2=C (MSB), INH tied low.
// Truth table is plain binary: code 0 = Y0, 1 = Y1 ... 7 = Y7.
// (Edit these only if the PCB routes the Y pins to pads in a different order.)
static const uint8_t ROW_CODE[8] = {0, 1, 2, 3, 4, 5, 6, 7};
static const uint8_t COL_CODE[8] = {0, 1, 2, 3, 4, 5, 6, 7};

FDC2214 fdc1(FDC2214_I2C_ADDR_1);   // the address that works on this board with this driver

static inline void writeMux(int s2, int s1, int s0, uint8_t code) {
    digitalWrite(s2, (code >> 2) & 1);
    digitalWrite(s1, (code >> 1) & 1);
    digitalWrite(s0, code & 1);
}

void setup() {
    Wire.begin();
    Wire.setClock(100000);   // slow bus while the FDC starts up; raised to 400 kHz below
    Serial.begin(SERIAL_BAUD);

    pinMode(MUX_COL_S2, OUTPUT); pinMode(MUX_COL_S1, OUTPUT); pinMode(MUX_COL_S0, OUTPUT);
    pinMode(MUX_ROW_S2, OUTPUT); pinMode(MUX_ROW_S1, OUTPUT); pinMode(MUX_ROW_S0, OUTPUT);
    writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, COL_CODE[0]);
    writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, ROW_CODE[0]);

    delay(100);   // let the FDC2214 finish powering up before the first I2C read
    bool ok = false;
    for (int attempt = 0; attempt < 10 && !ok; attempt++) {
        ok = fdc1.begin(0x01, 0x04, 0x05, true);   // CH0 only, internal oscillator
        if (!ok) delay(50);
    }
    Wire.setClock(400000);
    Serial.println();
    Serial.println(ok ? "# FDC2214 init OK" : "# FDC2214 init FAILED");   // '#' lines are ignored by the plot

    fdc1.enterSleepMode();                // single-conversion mode
    delay(100);
}

void loop() {
    uint32_t t0 = micros();

    for (int r = 0; r < ROWS; r++) {
        writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, ROW_CODE[r]);
        for (int c = 0; c < COLS; c++) {
            writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, COL_CODE[c]);
            fdc1.triggerSingleConversion(0);
            unsigned long raw = fdc1.getReading28(0);

            double pf = (double)computeCap_pf(raw);
            if (!isfinite(pf) || pf < 0.0) pf = 0.0;
            long milli_pf = lround(pf * 1000.0);

            Serial.printf("%d,%d,%ld\n", r, c, milli_pf);   // goes out while the next cell converts
        }
    }

    Serial.printf("#frame_us=%lu\n", (unsigned long)(micros() - t0));
}