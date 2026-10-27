// 8x8 capacitance grid: FDC2214 (FDC2214x.h driver) + two 8:1 muxes on CH0.
//
// prints cap and grid location to serial monitor at 115200 baud
//     <row>,<col>,<milli-pF>        e.g.  3,5,299140   (= 299.140 pF)

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <FDC2214x.h>
#include "cap.h"            // provides computeCap_pf(raw)


//mux 1 control pins
#define MUX_COL_S2 19
#define MUX_COL_S1 18
#define MUX_COL_S0 5

//mux 2 control pins
#define MUX_ROW_S2 17 // TX2
#define MUX_ROW_S1 16 // RX2
#define MUX_ROW_S0 4

//control number of rows/cols in grid
constexpr int ROWS = 8;   
constexpr int COLS = 8;
uint8_t row,col = 0;

//use this to switch mapping of mux pins if wires are flipped or to orient graph in cap_heatmap.py
uint8_t ROW_ORDER[ROWS] = {7,6,5,4,3,2,1,0};
uint8_t COL_ORDER[COLS] = {0,1,2,3,4,5,7,6};

FDC2214 fdc1(FDC2214_I2C_ADDR_0);   // address when pulled low (0x2A)

//writes 3 bit value to mux
static inline void writeMux(int s2, int s1, int s0, uint8_t code) {
    digitalWrite(s2, (code >> 2) & 1);
    digitalWrite(s1, (code >> 1) & 1);
    digitalWrite(s0, code & 1);
}

void setup() {
    Wire.begin();
    Wire.setClock(400000);   
    Serial.begin(115200);

    bool ok = fdc1.begin(0x01, 0x04, 0x05, true); //initialize FDC if address found
    Serial.println("testing fdc");
    if (ok){
        Serial.println("fdc okay");
    }
    else {
        Serial.println("fdc not okay");
    }

    fdc1.enterSleepMode();
    delay(100);

    //initialize control pins
    pinMode(MUX_COL_S2, OUTPUT); pinMode(MUX_COL_S1, OUTPUT); pinMode(MUX_COL_S0, OUTPUT);
    pinMode(MUX_ROW_S2, OUTPUT); pinMode(MUX_ROW_S1, OUTPUT); pinMode(MUX_ROW_S0, OUTPUT);
    writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, col);
    writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, row);
}


//////////////////////////////////////////////////
///////////// Main cap sensing loop //////////////
//////////////////////////////////////////////////
void loop() {
    for (int col = 0; col < 8; col++) {            // col 0 = even, col 1 = odd
        writeMux(MUX_COL_S2, MUX_COL_S1, MUX_COL_S0, COL_ORDER[col]);
        for (int row = 0; row < 8; row++) {
            writeMux(MUX_ROW_S2, MUX_ROW_S1, MUX_ROW_S0, ROW_ORDER[row]);
        
            fdc1.triggerSingleConversion(0);
            unsigned long raw = fdc1.getReading28(0); //28 bit reading

            double pf = (double)computeCap_pf(raw);
            if (pf > 2000.0 || pf < 0){
                pf = 0.0;
            }
            
            long milli_pf = lround(pf * 1000.0);
            Serial.printf("%d,%d,%ld\n", row, col, milli_pf);   // goes out while the next cell converts   
          
        }
    }
}


//////////////////////////////////////////////////
///////////// I2C Device Scan ////////////////////
//////////////////////////////////////////////////

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