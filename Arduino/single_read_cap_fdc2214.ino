// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: Copyright (c) 2026 Ashwin Whitchurch, Protocentral Electronics

/*
 * 04_Capacitance - Convert FDC2214 frequency to picofarads
 *
 * Copyright (c) 2026 Ashwin Whitchurch, Protocentral Electronics
 * Email: info@protocentral.com
 *
 * Converts the ProtoCentral FDC2214 frequency reading into picofarads using
 * the LC resonance equation:
 *
 *     C = 1 / (L * (2*pi*f)^2)
 *
 * You must tell the library the value of the inductor used in your LC tank.
 * The ProtoCentral FDC2214 breakout uses a 15 uH inductor with a 33 pF cap.
 *
 * This software is licensed under the MIT License.
 */

//////////////////////////////////////////////////////////////////////////////////////////
//
//    Hardware Setup:
//      Connect your LC tank between IN0A and IN0B.
//        3.3V -> VCC
//        GND  -> GND
//        SDA  -> SDA (A4 on Uno)
//        SCL  -> SCL (A5 on Uno)
//
/////////////////////////////////////////////////////////////////////////////////////////

#include <Wire.h>
#include <Protocentral_FDC2214.h>

// >>> EDIT THIS to match your tank inductor <<<
const float TANK_INDUCTANCE_UH = 18.0f;

FDC2214 fdc;

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Wire.begin();

    if (!fdc.begin()) {
        Serial.println(F("FDC2214 not found"));
        while (1) delay(1000);
    }

    fdc.configureDefaults();
    fdc.setActiveChannel(FDC2214_CH0);
    fdc.setAutoscan(false);
    fdc.start();

    Serial.print(F("Tank inductor: "));
    Serial.print(TANK_INDUCTANCE_UH);
    Serial.println(F(" uH"));
    Serial.println(F("Freq (MHz)\tC (pF)"));
}

void loop() {
    if (fdc.isDataReady(FDC2214_CH0)) {
        float f_hz = fdc.readFrequencyHz(FDC2214_CH0);
        float c_pf = fdc.readCapacitancePf(FDC2214_CH0, TANK_INDUCTANCE_UH);

        Serial.print(f_hz / 1.0e6f, 6);
        Serial.print('\t');
        Serial.println(c_pf, 4);
    }
    delay(10);
}
