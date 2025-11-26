#include <Wire.h>
#include "FDC2214.h"

FDC2214 capsense(FDC2214_I2C_ADDR_0);

#define SAMPLE_INTERVAL_MS 50      // 20 Hz sampling during baseline
#define BASELINE_TIME_MS   10000    // 10 seconds
#define MAX_SAMPLES        (BASELINE_TIME_MS / SAMPLE_INTERVAL_MS)

unsigned long baselineSamples[MAX_SAMPLES];
int sampleCount = 0;
unsigned long baselineMedian = 0;
bool baselineSet = false;

// -------- median helper ---------
unsigned long computeMedian(unsigned long *arr, int n) {
  // simple insertion sort (n <= 200)
  for (int i = 1; i < n; i++) {
    unsigned long key = arr[i];
    int j = i - 1;

    while (j >= 0 && arr[j] > key) {
      arr[j + 1] = arr[j];
      j--;
    }
    arr[j + 1] = key;
  }
  return arr[n / 2];
}

// -------- setup --------
void setup() {
  Wire.begin();
  Serial.begin(115200);
  delay(300);

  Serial.println("\nFDC2214 Median Baseline ΔC/C Mode");

  bool ok = capsense.begin(
    0x01,   // CH0 only
    0x00,   // no autoscan
    0x01,   // 1 MHz deglitch
    true    // internal oscillator
  );
  Serial.println(ok ? "Sensor OK" : "Sensor FAIL");

  Serial.println("Collecting baseline for 10 seconds...");
}

// -------- loop --------
void loop() {
  // --- baseline acquisition ---
  if (!baselineSet) {
    if (sampleCount < MAX_SAMPLES) {
      unsigned long r = capsense.getReading28(0);
      baselineSamples[sampleCount++] = r;
      delay(SAMPLE_INTERVAL_MS);
      return;
    }

    // compute median
    baselineMedian = computeMedian(baselineSamples, sampleCount);
    baselineSet = true;

    Serial.print("Baseline Median = ");
    Serial.println(baselineMedian);
    Serial.println("Starting ΔC/C reporting...");
    return;
  }

  // --- normal mode ---
  unsigned long reading = capsense.getReading28(0);

  long delta = (long)reading - (long)baselineMedian;

  // deltaC/C = -(deltaFreq / freq)
  float deltaC_over_C = -( (float)delta / (float)baselineMedian );

  Serial.print("Raw: ");
  Serial.print(reading);
  Serial.print("  Δ: ");
  Serial.print(delta);
  Serial.print("  ΔC/C: ");
  Serial.println(deltaC_over_C, 6);

  delay(1000);  // 1 Hz reporting
}
