// 8x8 capacitance grid: FDC2214 (FDC2214x.h driver) + two 8:1 muxes on CH0.
//
// BINARY STREAMING: every cell is sent the moment it is read, as a 5-byte packet:
//     [0xA5] [index] [value low byte] [value high byte] [checksum]
//   index     = row*8 + col                      (0..63)
//   value     = capacitance in 1/100 pF, uint16  (51234 = 512.34 pF, max 655.35 pF)
//   checksum  = index ^ low ^ high ^ 0x5A        (lets the PC resync if a byte is lost)
// After each full scan one extra packet with index 0xFE carries the scan time
// in units of 100 microseconds.
#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <FDC2214x.h>
#include "cap.h"            // provides computeCap_pf(raw)

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
// So logical row/col N uses code N, i.e. Y0 <-> row/col 0.
// (Edit these only if the PCB routes the Y pins to pads in a different order.)
static const uint8_t ROW_CODE[8] = {0, 1, 2, 3, 4, 5, 6, 7};
static const uint8_t COL_CODE[8] = {0, 1, 2, 3, 4, 5, 6, 7};

FDC2214 fdc1(FDC2214_I2C_ADDR_1);

static inline void writeMux(int s2, int s1, int s0, uint8_t code) {
    digitalWrite(s2, (code >> 2) & 1);
    digitalWrite(s1, (code >> 1) & 1);
    digitalWrite(s0, code & 1);
}

// NOTE: Serial.write(uint16_t) only sends the LOW byte, so we build the bytes ourselves.
static inline void sendPacket(uint8_t idx, uint16_t value) {
    uint8_t lo = value & 0xFF;
    uint8_t hi = value >> 8;
    uint8_t pkt[5] = {0xA5, idx, lo, hi, (uint8_t)(idx ^ lo ^ hi ^ 0x5A)};
    Serial.write(pkt, sizeof(pkt));
}

void setup() {
    Wire.begin();
    Wire.setClock(400000);
    Serial.begin(921600);

    pinMode(MUX_COL_S2, OUTPUT); pinMode(MUX_COL_S1, OUTPUT); pinMode(MUX_COL_S0, OUTPUT);
    pinMode(MUX_ROW_S2, OUTPUT); pinMode(MUX_ROW_S1, OUTPUT); pinMode(MUX_ROW_S0, OUTPUT);
    writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, COL_CODE[0]);
    writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, ROW_CODE[0]);

    fdc1.begin(0x01, 0x04, 0x05, true);   // CH0 only, internal oscillator
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
            double centi = pf * 100.0 + 0.5;                      // round to 0.01 pF
            uint16_t v = centi > 65535.0 ? 65535 : (uint16_t)centi;  // clamp instead of wrapping

            sendPacket(r * 8 + c, v);     // goes out while the next cell converts
        }
    }

    uint32_t t = (micros() - t0) / 100;   // scan time in 100 us units
    sendPacket(0xFE, t > 65535 ? 65535 : (uint16_t)t);
}