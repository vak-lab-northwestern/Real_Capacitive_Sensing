// Pins
const int DIR_PIN   = 2;
const int STEP_PIN  = 3;
// const int ms1 = 8;
// const int ms2 = 9;
// const int ms3 = 10; // 8, 9, 10 added for microstepping

// Optional: tie to A4988 EN if you wired it. LOW=enabled, HIGH=disabled
// const int ENABLE_PIN = 4;  // comment out if unused

// Mechanics & target
const float spoolDiameterMM = 23.4;  // fixed hub diameter
const int   fullStepsPerRev = 200;   // NEMA 23 or NEMA 17
const int   microstep       = 32;    // set with DIP switches on Microstep Driver
const float speedMMperS     = 2.5;   // target linear speed
const float pauseDurationS  = 0;    // duration of pause for drying in seconds
const float pauseIntervalCM = 60;    // length interval between pauses for drying, in cm

// Timing (computed)
unsigned long stepInterval_us;
unsigned long nextStepAt_us;
unsigned long pauseInterval_us;
unsigned long nextPauseAt_us;
unsigned long pauseDuration_ms;

void setup() {
  Serial.begin(9600);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  // pinMode(ENABLE_PIN, OUTPUT);
  // pinMode(ms1, OUTPUT); // microstep
  // pinMode(ms2, OUTPUT); // microstep
  // pinMode(ms3, OUTPUT); // microstep

  digitalWrite(DIR_PIN, HIGH);     // choose direction
  // digitalWrite(ENABLE_PIN, LOW);   // enable driver outputs
 
 // 1/16 step
  // digitalWrite(ms1, HIGH);
  // digitalWrite(ms2, HIGH);
  // digitalWrite(ms3, HIGH);

  const float mmPerRev   = 3.14159265f * spoolDiameterMM;
  const float stepsPerMM = (fullStepsPerRev * (float)microstep) / mmPerRev;
  const float stepsPerS  = stepsPerMM * speedMMperS;

  stepInterval_us = (unsigned long)(1000000.0f / stepsPerS); // ≈ 154,600 µs
  nextStepAt_us   = micros() + stepInterval_us;

  pauseInterval_us = (unsigned long)(pauseIntervalCM / (speedMMperS / 10) ) * 1000000.0f;
  pauseDuration_ms = (unsigned long)(pauseDurationS * 1000);
  nextPauseAt_us  = micros() + pauseInterval_us;
  Serial.println("Start");
}

void loop() {
  // outer loop to pause for drying
  unsigned long outer_now = micros();
  if ((long)(outer_now - nextPauseAt_us) >= 0) {
    Serial.println(pauseInterval_us);
    
    delay(pauseDuration_ms);

    nextPauseAt_us = outer_now + pauseInterval_us + pauseDuration_ms*1000;
  }


  // Don't do anything if speed is set to 0 mm/s
  if (speedMMperS == 0.0){
    return;
  }

  // wait until it's time for the next step
  unsigned long now = micros();
  if ((long)(now - nextStepAt_us) >= 0) {
    // 1 step: short HIGH pulse then LOW
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(5);          // pulse width
    digitalWrite(STEP_PIN, LOW);

    nextStepAt_us = now + stepInterval_us; // schedule next step
  }

  // optional: do other work here (non-blocking)
  
  
}