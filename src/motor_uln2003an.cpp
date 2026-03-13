#include <Stepper.h>

#define STEPS 100

Stepper stepper(STEPS, 8, 9, 10, 11);

void setup() {

    stepper.setSpeed(30);                   

}

void loop() {

    stepper.step(150);                      

}