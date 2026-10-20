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



#define MUX_COL_S2 19
#define MUX_COL_S1 18
#define MUX_COL_S0 5
#define MUX_ROW_S2 17
#define MUX_ROW_S1 16
#define MUX_ROW_S0 4

constexpr int ROWS = 8;   
constexpr int COLS = 8;
uint8_t r,c = 0;

//use this to switch mapping of mux pins if wires are flipped
uint8_t ROW_ORDER[ROWS] = {7,6,5,4,3,2,1,0};
uint8_t COL_ORDER[COLS] = {0,1,2,3,4,5,7,6};

FDC2214 fdc1(FDC2214_I2C_ADDR_0);   // address when pulled low (0x2A)

static inline void writeMux(int s2, int s1, int s0, uint8_t code) {
    digitalWrite(s2, (code >> 2) & 1);
    digitalWrite(s1, (code >> 1) & 1);
    digitalWrite(s0, code & 1);
}

void setup() {
    Wire.begin();
    Wire.setClock(400000);   // slow bus while the FDC starts up; raised to 400 kHz below
    
    Serial.begin(115200);

    bool ok = fdc1.begin(0x01, 0x04, 0x05, true);
    Serial.println("testing fdc");
    if (ok){
        Serial.println("fdc okay");
    }
    else {
        Serial.println("fdc not okay");
    }
    fdc1.enterSleepMode();
    delay(100);


    Serial.println();
    Serial.println("# BUILD " __DATE__ " " __TIME__);

    pinMode(MUX_COL_S2, OUTPUT); pinMode(MUX_COL_S1, OUTPUT); pinMode(MUX_COL_S0, OUTPUT);
    pinMode(MUX_ROW_S2, OUTPUT); pinMode(MUX_ROW_S1, OUTPUT); pinMode(MUX_ROW_S0, OUTPUT);
    writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, c);
    writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, r);

    // delay(100);   // let the FDC2214 finish powering up before the first I2C read
    // bool ok = false;
    // for (int attempt = 0; attempt < 10 && !ok; attempt++) {
    //     ok = fdc1.begin(0x01, 0x04, 0x05, true);   // CH0 only, internal oscillator
    //     if (!ok) delay(50);
    //     //Serial.println("hi");
    // }
    // Wire.setClock(400000);
    // Serial.println();
    // Serial.println(ok ? "# FDC2214 init OK" : "# FDC2214 init FAILED");   // '#' lines are ignored by the plot

    //fdc1.enterSleepMode();                // single-conversion mode
    delay(100);
}

// void loop() {
//     uint32_t t0 = micros();

//     for (int r = 0; r < ROWS; r++) {
//         writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, r);
//         for (int c = 0; c < COLS; c++) {
//             writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, c);
//             fdc1.triggerSingleConversion(0);
//             unsigned long raw = fdc1.getReading28(0);

//             double pf = (double)computeCap_pf(raw);
//             if (!isfinite(pf) || pf < 0.0) pf = 0.0;
//             long milli_pf = lround(pf * 1000.0);

//             Serial.printf("%d,%d,%ld\n", r, c, milli_pf);   // goes out while the next cell converts
//         }
//     }

//     Serial.printf("#frame_us=%lu\n", (unsigned long)(micros() - t0));
// // }
void loop() {
    for (int col = 0; col < 8; col++) {            // col 0 = even, col 1 = odd
        writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, COL_ORDER[col]);
        for (int r = 0; r < 8; r++) {
            writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, ROW_ORDER[r]);
            // Serial.printf("reading row mux pin: %d \n", ROW_ORDER[r]);
            // Serial.printf("reading col mux pin: %d \n", COL_ORDER[col]);
            // Serial.printf("mapping to grid position: row=%d, col=%d \n \n", r, col);
            fdc1.triggerSingleConversion(0);
            unsigned long raw = fdc1.getReading28(0); //28 bit reading

            double pf = (double)computeCap_pf(raw);
           
            long milli_pf = lround(pf * 1000.0);
           Serial.printf("%d,%d,%ld\n", r, col, milli_pf);   // goes out while the next cell converts   
          
        }
    }
}

    //delay(1000);

// void loop(){
// byte error, address;
//   int nDevices = 0;

//   Serial.println("Scanning...");

//   for (address = 1; address < 127; address++) {
//     // The i2c_scanner uses the return value of
//     // Wire.endTransmission() to see if
//     // a device acknowledged the address.
//     Wire.beginTransmission(address);
//     error = Wire.endTransmission();

//     if (error == 0) {
//       Serial.print("I2C device found at address 0x");
//       if (address < 16) {
//         Serial.print("0");
//       }
//       Serial.print(address, HEX);
//       Serial.println(" !");
//       nDevices++;
//     } else if (error == 4) {
//       Serial.print("Unknown error at address 0x");
//       if (address < 16) {
//         Serial.print("0");
//       }
//       Serial.println(address, HEX);
//     }
//   }

//   if (nDevices == 0) {
//     Serial.println("No I2C devices found\n");
//   } else {
//     Serial.println("Done\n");
//   }

//   delay(5000); // Wait 5 seconds before the next scan
// }