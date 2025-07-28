#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"


FDC2214 capsense(FDC2214_I2C_ADDR_0); // Use FDC2214_I2C_ADDR_1 

// ###
void setup() {
  
  // ### Start I2C 
  Wire.begin();
//  Wire.setClock(400000L);
  
  // ### Start serial
  Serial.begin(115200);
  Serial.println("\nFDC2x1x Raw");
  
  // Start FDC2214 with 4 channels init
  bool capOk = capsense.begin(0xF, 0x6, 0x5, false); //setup all four channels, autoscan with 4 channels, deglitch at 10MHz, external oscillator 
  if (capOk) Serial.println("Sensor OK");  
  else Serial.println("Sensor Fail");  

}

#define CHAN_COUNT 4

// ### 
void loop() {
  unsigned long capa[CHAN_COUNT]; // variable to store data from FDC
  for (int i = 0; i < CHAN_COUNT; i++){ // for each channel
    // Read 28bit data
    capa[i]= capsense.getReading28(i);//  
    // Python readable format
    Serial.print(capa[i]);  
    if (i < CHAN_COUNT-1) Serial.print(", ");
    else Serial.println("");
  }

  delay(100); 
}

// // Create FDC2214 object at I2C address 0
// FDC2214 capsense(FDC2214_I2C_ADDR_0);

// // Constants
// const float ref_clock = 40e6;        // 40 MHz reference clock
// const float inductance = 180e-9;     // 180 nH inductor value
// const float scale_factor = ref_clock / pow(2, 28);  // ~0.149 Hz per LSB

// #define CHAN_COUNT 4  // Number of active sensor channels

// void setup() {
//   // Initialize I2C and Serial
//   Wire.begin();
//   Serial.begin(115200);
//   Serial.println("\nFDC2x1x test");

//   // Check for I2C device
//   Serial.print("Scanning I2C... ");
//   Wire.beginTransmission(FDC2214_I2C_ADDR_0);
//   if (Wire.endTransmission() == 0) Serial.println("Device found!");
//   else Serial.println("No response");

//   // Initialize FDC2214 with 2 channels, 10 MHz deglitch filter, external oscillator
//   bool capOk = capsense.begin(0xF, 0x4, 0x5, false);
//   if (capOk) Serial.println("Sensor OK");
//   else Serial.println("Sensor Fail");
// }


// void loop() {
//   unsigned long capa[CHAN_COUNT];

//   for (int i = 0; i < CHAN_COUNT; i++) {
//     capa[i] = capsense.getReading28(i);
//   }

//   // Print all three capacitance values in one comma-separated line
//   for (int i = 0; i < CHAN_COUNT; i++) {
//     float freq = capa[i] * scale_factor;
//     float capacitance_F = 1.0 / (pow(2 * M_PI * freq, 2) * inductance);
//     float capacitance_pF = capacitance_F * 1e12;

//     Serial.print(capacitance_pF, 6);  // Print with 6 decimal places
//     if (i < CHAN_COUNT - 1) Serial.print(",");  // Add comma except after last
//   }

//   Serial.println();  // End of line
//   delay(100); // ~10Hz update rate
// }  