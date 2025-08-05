#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

FDC2214 capsense0(FDC2214_I2C_ADDR_0); // Use FDC2214_I2C_ADDR_1 
FDC2214 capsense1(FDC2214_I2C_ADDR_1);

void setup() {
  
  // ### Start I2C 
  Wire.begin();
  
  // ### Start serial
  Serial.begin(115200);
  Serial.println("\nFDC2x1x Raw");
  
  // Start FDC2214 with 4 channels init
  bool capO = capsense0.begin(0xF, 0x6, 0x5, false); //setup all four channels, autoscan with 4 channels, deglitch at 10MHz, external oscillator 
  bool cap1 = capsense1.begin(0xF, 0x6, 0x5, false); 
  if (capO) Serial.println("Sensor OK");  
  else Serial.println("Sensor Fail");  
  
  if (cap1) Serial.println("Sensor OK");  
  else Serial.println("Sensor Fail");  

}

#define CHAN_COUNT 4

// ### 
void loop() {
  unsigned long capa0[CHAN_COUNT]; // variable to store data from FDC but not necessary if only directly reading and processing else where
  unsigned long capa1[CHAN_COUNT];
  for (int i = 0; i < CHAN_COUNT; i++){ // for each channel
    // Read 28bit data
    capa0[i]= capsense0.getReading28(i);//  
    capa1[i]= capsense1.getReading28(i);

  }

  // Print sensor 0
  Serial.print("Chip0: ");
  for (int i = 0; i < CHAN_COUNT; i++) {
    Serial.print(capa0[i]);
    if (i < CHAN_COUNT-1) Serial.print(", ");
  }
  Serial.println();

  // Print sensor 1
  Serial.print("Chip1: ");
  for (int i = 0; i < CHAN_COUNT; i++) {
    Serial.print(capa1[i]);
    if (i < CHAN_COUNT-1) Serial.print(", ");
  }
  Serial.println();

  delay(1000); 
}

