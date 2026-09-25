// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: Copyright (c) 2026 Ashwin Whitchurch, Protocentral Electronics

/*
 * 03_MultiChannelAutoScan - 4-channel autoscan
 *
 * Copyright (c) 2026 Ashwin Whitchurch, Protocentral Electronics
 * Email: info@protocentral.com
 *
 * Enables autoscan over all four channels of the ProtoCentral FDC2214 and
 * prints the sensor frequency for each in a tab-separated row suitable for
 * the Arduino Serial Plotter. Channels with no tank attached will read 0 or
 * report amplitude errors.
 *
 * This software is licensed under the MIT License.
 */

//////////////////////////////////////////////////////////////////////////////////////////
//
//    Hardware Setup:
//      Connect an LC tank to each of CH0..CH3 (IN0A/IN0B .. IN3A/IN3B).
//        3.3V -> VCC
//        GND  -> GND
//        SDA  -> SDA (A4 on Uno)
//        SCL  -> SCL (A5 on Uno)
//
/////////////////////////////////////////////////////////////////////////////////////////

#include <Wire.h>
#include <Protocentral_FDC2214.h>

FDC2214 fdc;
const float TANK_INDUCTANCE_H = 18.0 * 1.0e-6f;

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Wire.begin();

    if (!fdc.begin()) {
        Serial.println(F("FDC2214 not found"));
        while (1) delay(1000);
    }

    fdc.configureDefaults();
    fdc.setAutoscan(true, FDC2214_RR_SEQ_ALL);
    fdc.start();

    Serial.println(F("CH0_f\tCH1_f\tCH2_f\tCH3_f   (MHz)"));
}

void loop() {
    float f[4];
    float c[4];
    float w;
    float raw_f;
    for (uint8_t ch = 0; ch < 4; ch++) {
        raw_f = fdc.readFrequencyHz((fdc2214_channel_t)ch);
        f[ch] = raw_f / 1.0e6f;
        w = 2.0f * (float)PI * raw_f;
        c[ch] = (1.0f / (TANK_INDUCTANCE_H * w * w)) * 1.0e12f; //convert to picofards at end
    }

    Serial.print(f[0], 5); Serial.print('\t');
    Serial.print(f[1], 5); Serial.print('\t');
    Serial.print(f[2], 5); Serial.print('\t');
    Serial.println(f[3], 5);

    Serial.print(c[0], 5); Serial.print('\t');
    Serial.print(c[1], 5); Serial.print('\t');
    Serial.print(c[2], 5); Serial.print('\t');
    Serial.println(c[3], 5);


    delay(10);
}
