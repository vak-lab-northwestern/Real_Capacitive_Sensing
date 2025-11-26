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

double baselineCap_pf = 0.0;


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

// ------------ convert raw reading → capacitance in pF -------------
double computeCap_pf(unsigned long reading) {
  const double fref = 40000000.0;  // 40 MHz internal reference
  const double L = 18e-6;          // 18 uH inductor
  const double Cboard = 33e-12;    // 33 pF fixed board capacitor
  const double Cpar = 3e-12;       // parasitics (adjust if needed)

  // Convert raw code → frequency
  double fs = (fref * (double)reading) / 268435456.0; // 2^28

  // LC resonance equation → total capacitance
  double Ctotal = 1.0 / ( (2.0 * M_PI * fs) * (2.0 * M_PI * fs) * L );

  // Remove board + parasitic capacitance
  double Csensor = Ctotal - (Cboard + Cpar);

  return Csensor * 1e12; // convert to picofarads
}


// ================== LOOP ==================
void loop() {
  // --- baseline acquisition ---
  if (!baselineSet) {
    if (sampleCount < MAX_SAMPLES) {
      unsigned long r = capsense.getReading28(0);
      baselineSamples[sampleCount++] = r;
      delay(SAMPLE_INTERVAL_MS);
      return;
    }

    // compute median raw reading
    baselineMedian = computeMedian(baselineSamples, sampleCount);

    // convert baseline reading → baseline capacitance
    baselineCap_pf = computeCap_pf(baselineMedian);

    baselineSet = true;

    Serial.print("Baseline Median Raw = ");
    Serial.println(baselineMedian);
    Serial.print("Baseline Capacitance = ");
    Serial.print(baselineCap_pf, 3);
    Serial.println(" pF");
    Serial.println("Starting ΔC reporting in pF...");
    return;
  }

  // --- normal mode ---
  unsigned long reading = capsense.getReading28(0);

  // current capacitance in pF
  double C_now_pf = computeCap_pf(reading);

  // delta capacitance in pF
  double deltaC_pf = C_now_pf - baselineCap_pf;

  // percent change if you still want it
  double deltaC_over_C = deltaC_pf / baselineCap_pf;

  Serial.print("C = ");
  Serial.print(C_now_pf, 3);
  Serial.print(" pF   ΔC = ");
  Serial.print(deltaC_pf, 3);
  Serial.print(" pF   ΔC/C = ");
  Serial.println(deltaC_over_C, 6);

  delay(1000);  // 1 Hz
}
