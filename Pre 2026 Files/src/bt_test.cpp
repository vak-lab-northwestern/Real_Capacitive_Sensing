#include <Arduino.h>
#include <SoftwareSerial.h>

void setup() {
  // This opens the hardware serial port at 115200 baud.
  // Both your PC (via USB) and the HC-06 are now on this line.
  Serial.begin(115200); 
  
  // Note: Since they share a line, what you send from the PC 
  // will be seen by the HC-06, and vice versa.
}

void loop() {
  // Check if data is coming in from either the PC or Bluetooth
  if (Serial.available()) {
    char data = Serial.read();
    
    // Echo it back so you can see it on both ends
    Serial.print("Data Received: ");
    Serial.println(data);
  }
}