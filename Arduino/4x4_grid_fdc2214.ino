#include <Wire.h>

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);  // SDA, SCL on ESP32
    delay(1000);

    Serial.println("Scanning I2C bus...");

    

    
}

void loop() {
  int devices = 0;
  for (byte address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();

        if (error == 0) {
            Serial.print("Device found at 0x");
            Serial.println(address, HEX);
            devices++;
        }
    }

    if (devices == 0) {
        Serial.println("No I2C devices found.");
    }
}