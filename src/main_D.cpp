#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

/*
  Working code for 2 chip configuration
  Initiating FDC2214 chip addresses 
  Only 2 possible configurations 
  ADDR_0 = 0x2A
  ADDR_1 = 0x2B
*/
FDC2214 capsense0(FDC2214_I2C_ADDR_0); 
// FDC2214 capsense1(FDC2214_I2C_ADDR_1);

// Variable definition
#define CHAN_COUNT 2

void setup() {
  
  /* Initializing I2C communication protocal */
  Wire.begin();
  Wire.setClock(400000);
  
  /* Configuring baud rate */
  Serial.begin(115200);
  
  /* Setup first four channels, autoscan with 4 channels, deglitch at 10MHz, external oscillator */
  bool capO = capsense0.begin(0x1, 0x4, 0x5, true); 
  // bool cap1 = capsense1.begin(0xF, 0x6, 0x5, true); 

  /* Checking if both sensors are being read on the same communication bus */
  if (capO) Serial.println("Sensor OK");  
  else Serial.println("Sensor Fail");  
  // if (cap1) Serial.println("Sensor OK");  
  // else Serial.println("Sensor Fail");  

}

void loop() {
  /* Storing data into list but not necessary since it is not being processed here */
  // unsigned long capa0[CHAN_COUNT]; 
  // unsigned long capa1[CHAN_COUNT];

  // /* Continuous reading of 28 bit data */
  // for (int i = 0; i < CHAN_COUNT; i++){ 
  //   capa0[i]= capsense0.getReading28(i);//  
  //   // capa1[i]= capsense1.getReading28(i);
  // }

  /* Printing results for Chip 0 (0x2A) in Python readable format */
  for (int i = 0; i < CHAN_COUNT; i++) {
    Serial.print(capsense0.getReading28(i));
    if (i < CHAN_COUNT - 1) Serial.print(", ");
  }

  /* Printing results for Chip 0 (0x2B) in Python readable format */
  // for (int i = 0; i < CHAN_COUNT; i++) {
    // Serial.print(capa1[i]);
    // if (i < CHAN_COUNT - 1) Serial.print(", ");
  // }
  Serial.println();
}

