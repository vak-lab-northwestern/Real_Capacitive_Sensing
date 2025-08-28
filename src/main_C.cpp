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

// Variable definition
#define CHAN_COUNT 2
#define Button 4
#define Num_1 6   // A (LSB)
#define Num_2 7   // B
#define Num_3 8   // C (MSB)

int muxState = 0;  

void setup() {
  Wire.begin();

  Serial.begin(9600);
  pinMode(Num_1, OUTPUT);
  pinMode(Num_2, OUTPUT);
  pinMode(Num_3, OUTPUT);
  pinMode(Button, INPUT_PULLUP);

  digitalWrite(Num_1, LOW);
  digitalWrite(Num_2, LOW);
  digitalWrite(Num_3, LOW);
  
  bool capO = capsense0.begin(0x3, 0x4, 0x5, false); 

  /* Checking if sensor is being read on the same communication bus */
  if (capO) Serial.println("Sensor OK");  
  else Serial.println("Sensor Fail");  
  
 }

void setMux(int state) {
  // Convert counter into binary CBA (LSB = A = Num_1)
  digitalWrite(Num_1, state & 0x01);  // A
  digitalWrite(Num_2, (state >> 1) & 0x01);  // B
  digitalWrite(Num_3, (state >> 2) & 0x01);  // C
}

void loop() {
  unsigned long capa0[CHAN_COUNT]; 

  for (int i = 0; i < CHAN_COUNT; i++){ 
    capa0[i]= capsense0.getReading28(i);
  }

  for (int i = 0; i < CHAN_COUNT; i++) {
    Serial.print(capa0[i]);
    if (i < CHAN_COUNT - 1) Serial.print(", ");
  }
  Serial.println();


  if (digitalRead(Button) == LOW) {
    muxState = (muxState + 1) % 8;   // cycle through 0–2
    setMux(muxState);

    // Serial.print("Mux State: ");
    // Serial.println(muxState);

    delay(200);  // debounce delay
  }
  delay(100);
}
 