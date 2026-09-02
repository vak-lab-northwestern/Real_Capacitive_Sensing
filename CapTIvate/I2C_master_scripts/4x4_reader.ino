
#include <Wire.h>

// ===== CapTIvate REGISTER_I2C Settings =====
#define CAPT_I2C_ADDR     0x0A   // I2C address of the CapTIvate target MCU
#define SENSOR_ID         0x00   // Sensor to read (0x00 = keypadSensor, per your setup)
#define NUM_CYCLES        4     // Number of time cycles for this sensor
#define ELEMENTS_PER_CYCLE 4     // Elements measured per cycle (adjust per-cycle if uneven)

// rx Cycle packet header is 6 bytes (0: CMD, 1: SensorID, 2: CycleID, 3-5: State(pressed or unpresseed)) 
// then 4 bytes per element (LTA Lower, LTA Upper, Count Lower, Count Upper)
#define HEADER_BYTES      6
#define BYTES_PER_ELEMENT 4

// ===== Storage for readings =====
// LTA and raw Count for every element, organized by [cycle][element]
uint16_t ltaValues[NUM_CYCLES][ELEMENTS_PER_CYCLE];
uint16_t countValues[NUM_CYCLES][ELEMENTS_PER_CYCLE];

// ===== Request one cycle packet and store its LTA/Count data =====
#line 21 "/Users/andresturullols/Downloads/captivate_lta_reader/captivate_lta_reader.ino"
void readCyclePacket(uint8_t sensorID, uint8_t cycleID);
#line 55 "/Users/andresturullols/Downloads/captivate_lta_reader/captivate_lta_reader.ino"
void setup();
#line 62 "/Users/andresturullols/Downloads/captivate_lta_reader/captivate_lta_reader.ino"
void loop();
#line 21 "/Users/andresturullols/Downloads/captivate_lta_reader/captivate_lta_reader.ino"
void readCyclePacket(uint8_t sensorID, uint8_t cycleID) {
  uint8_t tx[3];
  uint8_t packetLen = HEADER_BYTES + (BYTES_PER_ELEMENT * ELEMENTS_PER_CYCLE);
  uint8_t rx[HEADER_BYTES + (BYTES_PER_ELEMENT * ELEMENTS_PER_CYCLE)];

  // Build the 3-byte request: CMD=0x01 (cycle packet), Sensor ID, Cycle ID
  tx[0] = 0x01;
  tx[1] = sensorID;
  tx[2] = cycleID;

  Wire.beginTransmission(CAPT_I2C_ADDR);
  Wire.write(tx, 3);
  Wire.endTransmission(false);   // repeated start, keeps bus held for the slave's clock stretch

  Wire.requestFrom(CAPT_I2C_ADDR, packetLen);
  for (uint8_t i = 0; i < packetLen && Wire.available(); i++) {
    rx[i] = Wire.read();
  }

  // rx[0..2] = echoed CMD/SensorID/CycleID (confirmation, not data)
  // rx[3..5] = packed touch/proximity state bits (not used here)
  // rx[6...] = per-element LTA + Count, 4 bytes each

  for (uint8_t elem = 0; elem < ELEMENTS_PER_CYCLE; elem++) {
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
  Wire.setClock(400000);  // CapTIvate supports up to 400kHz per the doc
  delay(100);
}

void loop() {
  // Poll every cycle for the sensor
  for (uint8_t cycle = 0; cycle < NUM_CYCLES; cycle++) {
    readCyclePacket(SENSOR_ID, cycle);
  }

  // Print count and LTA values as CSVone line per scan, ordered by cycle then element
  // Format: count_c0e0,count_c0e1,count_c0e2,LTA_c0e3,LTA_c1e0,..., LTA_c0e0, LTA_c0e1,...
  for (uint8_t cycle = 0; cycle < NUM_CYCLES; cycle++) {
    for (uint8_t elem = 0; elem < ELEMENTS_PER_CYCLE; elem++) {
      Serial.print(countValues[cycle][elem]);
      Serial.print(",");
    }
  }
  for (uint8_t cycle = 0; cycle < NUM_CYCLES; cycle++) {
    for (uint8_t elem = 0; elem < ELEMENTS_PER_CYCLE; elem++) {
      Serial.print(ltaValues[cycle][elem]);
      bool isLast = (cycle == NUM_CYCLES - 1) && (elem == ELEMENTS_PER_CYCLE - 1);
      if (!isLast) Serial.print(",");
    }
  }
  Serial.println();

  delay(100);  // adjust scan rate as needed
}