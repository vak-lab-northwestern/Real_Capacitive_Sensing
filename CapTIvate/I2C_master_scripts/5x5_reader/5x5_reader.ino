#include <Wire.h>

// ===== CapTIvate REGISTER_I2C Settings =====
#define CAPT_I2C_ADDR       0x0A  // I2C address of the CapTIvate target MCU
#define SENSOR_ID           0x00  // Sensor to read (0x00 = keypadSensor)
#define NUM_CYCLES          10     // Number of time cycles for this sensor
#define MAX_ELEMENTS_PER_CYCLE 4
#define ELEMENTS_PER_ODD_CYCLE 4 // Num elements measured every odd cycle
#define ELEMENTS_PER_EVEN_CYCLE  1     // Num Elements measured every even cycle

// RX Cycle packet header: 6 bytes (CMD, SensorID, CycleID, 3x State) 
// Followed by 4 bytes per element (LTA Lower/Upper, Count Lower/Upper)
#define HEADER_BYTES        6
#define BYTES_PER_ELEMENT   4

// ===== Storage for readings =====
uint16_t ltaValues[NUM_CYCLES][MAX_ELEMENTS_PER_CYCLE];
uint16_t countValues[NUM_CYCLES][MAX_ELEMENTS_PER_CYCLE];

// ===== Function Declarations =====

void readCyclePacket(uint8_t sensorID, uint8_t cycleID, int num_elements) {
  uint8_t tx[3];
  int packetLen = HEADER_BYTES + (BYTES_PER_ELEMENT * num_elements);
  uint8_t rx[HEADER_BYTES + (BYTES_PER_ELEMENT * MAX_ELEMENTS_PER_CYCLE )];

  // Build the 3-byte request: CMD=0x01 (cycle packet), Sensor ID, Cycle ID
  tx[0] = 0x01;
  tx[1] = sensorID;
  tx[2] = cycleID;

  Wire.beginTransmission(CAPT_I2C_ADDR);
  Wire.write(tx, 3);
  Wire.endTransmission(false);   // repeated start, keeps bus held for clock stretch

  Wire.requestFrom((uint8_t)CAPT_I2C_ADDR, packetLen);
  for (uint8_t i = 0; i < packetLen && Wire.available(); i++) {
    rx[i] = Wire.read();
  }

  // Parse element values
  for (uint8_t elem = 0; elem < num_elements; elem++) {
    uint8_t base = HEADER_BYTES + (elem * BYTES_PER_ELEMENT);

    uint16_t lta   = (uint16_t)rx[base]     | ((uint16_t)rx[base + 1] << 8);
    uint16_t count = (uint16_t)rx[base + 2] | ((uint16_t)rx[base + 3] << 8);

    ltaValues[cycleID][elem]   = lta;
    countValues[cycleID][elem] = count;
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);  // CapTIvate supports up to 400kHz
  delay(100);
}

void loop() {
  // Poll every cycle for the sensor
  for (uint8_t cycle = 0; cycle < NUM_CYCLES; cycle++) {
    int num_elements = (cycle % 2 == 0) ? ELEMENTS_PER_EVEN_CYCLE : ELEMENTS_PER_ODD_CYCLE;
    readCyclePacket(SENSOR_ID, cycle, num_elements);
  }

  // Print all values as CSV: one line per scan
  for (uint8_t cycle = 0; cycle < NUM_CYCLES; cycle++) {
    int num_elements = (cycle % 2 == 0) ? ELEMENTS_PER_EVEN_CYCLE : ELEMENTS_PER_ODD_CYCLE;
    for (uint8_t elem = 0; elem < num_elements; elem++) {
      Serial.print(countValues[cycle][elem]);
      
      bool isLast = (cycle == NUM_CYCLES - 1) && (elem == num_elements - 1);
      if (!isLast) Serial.print(",");
    }
  }
  Serial.println();

  delay(100);  // Adjust scan rate as needed
}