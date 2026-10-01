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
//        SDA  -> SDA (21 on Esp32)
//        SCL  -> SCL (22 on Esp32)
//
//      MUX
//        A,B (1,rows) -> 4,5 on Esp32
//        A,B (2,cols) -> 18, 19 on Esp32
//
/////////////////////////////////////////////////////////////////////////////////////////

#include <Wire.h>
#include <Protocentral_FDC2214.h>

// >>> EDIT THIS to match your tank inductor <<<
const float TANK_INDUCTANCE_UH = 18.0;
const int mux1_A = 17;
const int mux1_B = 5;
const int mux1_C = 18;

const int mux2_A = 4;
const int mux2_B = 16;
const int mux2_C = 19;

FDC2214 fdc;

void read_cap(){
    while(!fdc.isDataReady(FDC2214_CH0)){
     // Serial.println("waiting");
        
    }
    float c_pf = fdc.readCapacitancePf(FDC2214_CH0, TANK_INDUCTANCE_UH);
    Serial.print(c_pf, 4);
    Serial.print('\t');
   // delay(20);
}


void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Wire.begin();

    if (!fdc.begin()) {
        Serial.println(F("FDC2214 not found"));
        while (1) delay(1000);
    }

    pinMode(mux1_A, OUTPUT);
    pinMode(mux1_B, OUTPUT);
    pinMode(mux1_C, OUTPUT);
    pinMode(mux2_A, OUTPUT);
    pinMode(mux2_B, OUTPUT);
    pinMode(mux2_C, OUTPUT);

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


    for(int r = 0; r < 8; r++){
        if(r == 0){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, LOW);
            digitalWrite(mux1_C, LOW);
        }
        else if(r == 1){
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, LOW);
            digitalWrite(mux1_C, LOW);
        }
        else if(r == 2){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, HIGH);
            digitalWrite(mux1_C, LOW);
        }
        else if(r == 3){
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, HIGH);
            digitalWrite(mux1_C, LOW);
        }
        else if(r == 4){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, LOW);
            digitalWrite(mux1_C, HIGH);
        }
        else if(r == 5){
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, LOW);
            digitalWrite(mux1_C, HIGH);
        }
        else if(r == 6){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, HIGH);
            digitalWrite(mux1_C, HIGH);
        }
        else{ //r == 7
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, HIGH);
            digitalWrite(mux1_C, HIGH);
        }

        for(int c =0; c < 8; c++){
        if(c == 0){
            digitalWrite(mux2_A, LOW);
            digitalWrite(mux2_B, LOW);
            digitalWrite(mux2_C, LOW);
        }
        else if(c == 1){
            digitalWrite(mux2_A, HIGH);
            digitalWrite(mux2_B, LOW);
            digitalWrite(mux2_C, LOW);
        }
        else if(c == 2){
            digitalWrite(mux2_A, LOW);
            digitalWrite(mux2_B, HIGH);
            digitalWrite(mux2_C, LOW);
        }
        else if(c == 3){
            digitalWrite(mux2_A, HIGH);
            digitalWrite(mux2_B, HIGH);
            digitalWrite(mux2_C, LOW);
        }
        else if(c == 4){
            digitalWrite(mux2_A, LOW);
            digitalWrite(mux2_B, LOW);
            digitalWrite(mux2_C, HIGH);
        }
        else if(c == 5){
            digitalWrite(mux2_A, HIGH);
            digitalWrite(mux2_B, LOW);
            digitalWrite(mux2_C, HIGH);
        }
        else if(c == 6){
            digitalWrite(mux2_A, LOW);
            digitalWrite(mux2_B, HIGH);
            digitalWrite(mux2_C, HIGH);
        }
        else{ //c == 7
            digitalWrite(mux2_A, HIGH);
            digitalWrite(mux2_B, HIGH);
            digitalWrite(mux2_C, HIGH);
        }
            Serial.print(r);
            Serial.print(",");
            Serial.print(c);
            Serial.print(": ");
            read_cap();
        }
    }
    Serial.println(' ');
    //delay(1000);
}
