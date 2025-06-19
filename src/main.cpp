  #include <Arduino.h>
  #include <Wire.h>
  #include "FDC2214.h"



FDC2214 capsense(FDC2214_I2C_ADDR_0); // Use FDC2214_I2C_ADDR_1 

const int LED_1 = A1;
const int LED_2 = A2;

// ###
void setup() {
  // ### Start I2C 
  pinMode(LED_1, OUTPUT);
  pinMode(LED_2, OUTPUT);
  digitalWrite(LED_1, LOW); // Ensure LED1 is off initially
  digitalWrite(LED_2, LOW); 
  Wire.begin();
  //Wire.setClock(400000L);
  
  // ### Start serial
  Serial.println("\nFDC2x1x test");
  
  // ### Start FDC
  
  Serial.print("Scanning I2C... ");
  Wire.beginTransmission(FDC2214_I2C_ADDR_0); 
  if (Wire.endTransmission() == 0) Serial.println("Device found!");
  else Serial.println("No response, check wiring!");

  // Start FDC2212 with 2 channels init
  bool capOk = capsense.begin(0x3, 0x4, 0x5, false); //setup first two channels, autoscan with 2 channels, deglitch at 10MHz, external oscillator 
  // Start FDC2214 with 4 channels init
//  bool capOk = capsense.begin(0xF, 0x6, 0x5, false); //setup all four channels, autoscan with 4 channels, deglitch at 10MHz, external oscillator 
  // Start FDC2214 with 4 channels init
//  bool capOk = capsense.begin(0xF, 0x6, 0x5, true); //setup all four channels, autoscan with 4 channels, deglitch at 10MHz, internal oscillator 

}

// ### Tell aplication how many chanels will be smapled in main loop
#define CHAN_COUNT 2
#define THRESHOLD 20000


void loop() {
  unsigned long capa[CHAN_COUNT]; // variable to store data from FDC
  for (int i = 0; i < CHAN_COUNT; i++){ // for each channel
    // ### read 28bit data
    capa[i]= capsense.getReading28(i);//  
    // ### Transmit data to serial in simple format readable by SerialPlot application.
  }

  digitalWrite(LED_1, (capa[0] < THRESHOLD) ? HIGH : LOW);
  digitalWrite(LED_2, (capa[1] < THRESHOLD) ? HIGH : LOW);

  delay(100); // Small delay for stability
  // No point in sleeping
  //delay(100); 
}