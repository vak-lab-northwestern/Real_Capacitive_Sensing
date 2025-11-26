#include <Arduino.h>
#include <Wire.h>
#include "FDC2214.h"

/*
  FDC2214 Direct Channel Reading (No Multiplexers)
  Reads directly from all 4 FDC2214 channels (CH0, CH1, CH2, CH3) without using MUX.
  Output format to Serial (one line per channel):
  Timestamp,Channel_index,Node_Value
  where:
    Channel_index = FDC channel number (0-3)
    Node_Value = FDC raw 28-bit frequency reading (NOT capacitance in pF)
    
  Note: Node_Value is a frequency count from the FDC2214. Lower values = higher capacitance.
        To convert to capacitance: freq = Node_Value * (40MHz / 2^28)
                                   C = 1 / ((2π * freq)^2 * L)
        Typical values: 10-500pF sensors produce readings in range 100,000 - 15,000,000
*/

// Constants
#define NUM_CHANNELS 4         // FDC2214 has 4 channels (CH0, CH1, CH2, CH3)
#define FDC_CONVERSION_WAIT_MS 10  // Wait for FDC conversion cycle

FDC2214 fdc1(FDC2214_I2C_ADDR_0);

void initFDC(FDC2214 &fdc, const char *name) {
  // Configure FDC2214 to use all 4 channels with autoscan:
  // 0x0F = binary 1111 = All channels (CH0, CH1, CH2, CH3) enabled
  // 0x0F = autoscan sequence through all enabled channels
  // 0x05 = deglitch at 10MHz (reduces noise)
  // false = external oscillator
  bool ok = fdc.begin(0x0F, 0x0F, 0x05, false);   
  if (ok) Serial.print(name), Serial.println(" READY");
  else Serial.print(name), Serial.println(" FAIL");
}

void setup() {
  Wire.begin();
  Wire.setClock(400000);
  Serial.begin(115200);
  
  initFDC(fdc1, "FDC");
  
  // Let FDC stabilize before starting measurements
  delay(200);
  
  Serial.println("Timestamp,Channel_index,Node_Value");
}

void loop() {
  // Read directly from all 4 FDC2214 channels without loops
  // Each channel is read sequentially using its channel number
  
  unsigned long timestamp = millis();
  
  // Read CH0 directly
  uint32_t ch0_value = fdc1.getReading28(0);
  Serial.print(timestamp);
  Serial.print(",0,");
  Serial.println(ch0_value);
  
  delay(FDC_CONVERSION_WAIT_MS);
  
  // Read CH1 directly
  uint32_t ch1_value = fdc1.getReading28(1);
  Serial.print(timestamp);
  Serial.print(",1,");
  Serial.println(ch1_value);
  
  delay(FDC_CONVERSION_WAIT_MS);
  
  // Read CH2 directly
  uint32_t ch2_value = fdc1.getReading28(2);
  Serial.print(timestamp);
  Serial.print(",2,");
  Serial.println(ch2_value);
  
  delay(FDC_CONVERSION_WAIT_MS);
  
  // Read CH3 directly
  uint32_t ch3_value = fdc1.getReading28(3);
  Serial.print(timestamp);
  Serial.print(",3,");
  Serial.println(ch3_value);
  
  // Small delay before next scan cycle
  delay(10);
}
