

#include <Wire.h>
#include <Protocentral_FDC2214.h>

<<<<<<< Updated upstream:FDC2214/12x4_grid_fdc2214/12x4_grid_fdc2214.ino
// >>> EDIT THIS to match your tank inductor <<<
const float TANK_INDUCTANCE_UH = 18.0f;
const int mux1_A = 4;
const int mux1_B = 5;
const int mux2_A = 18;
const int mux2_B = 19;
=======
const float TANK_INDUCTANCE_UH = 18.0;
const int mux1_A = 6;
//const int mux1_B = 5;
//const int mux1_C = 18;

const int mux2_A = 38;
//const int mux2_B = 16;
//const int mux2_C = 19;

const int inh_A = 7;
const int inh_B = 47;
>>>>>>> Stashed changes:FDC2214/4x4_grid_fdc2214/4x4_grid_fdc2214.ino

FDC2214 fdc;

void read_cap(){
    while(!fdc.isDataReady(FDC2214_CH0)){
        
    }
    float c_pf = fdc.readCapacitancePf(FDC2214_CH0, TANK_INDUCTANCE_UH);
    Serial.print(c_pf, 4);
    Serial.print('\t');
    //delay(20);
}


void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Wire.begin();

    if (!fdc.begin()) {
        Serial.println(F("FDC2214 not found"));
        while (1) delay(1000);
    }

    pinMode(mux1_A, OUTPUT);
<<<<<<< Updated upstream:FDC2214/12x4_grid_fdc2214/12x4_grid_fdc2214.ino
    pinMode(mux1_B, OUTPUT);
    pinMode(mux2_A, OUTPUT);
    pinMode(mux2_B, OUTPUT);
=======
    //pinMode(mux1_B, OUTPUT);
    //pinMode(mux1_C, OUTPUT);
    pinMode(mux2_A, OUTPUT);
    pinMode(inh_A, OUTPUT);
    pinMode(inh_B, OUTPUT);
    //pinMode(mux2_B, OUTPUT);
   // pinMode(mux2_C, OUTPUT);

    digitalWrite(inh_A, LOW);
    digitalWrite(inh_B, LOW);
>>>>>>> Stashed changes:FDC2214/4x4_grid_fdc2214/4x4_grid_fdc2214.ino

    fdc.configureDefaults();
    fdc.setActiveChannel(FDC2214_CH0);
    fdc.setAutoscan(false);
    fdc.start();

    Serial.print(F("Tank inductor: "));
    Serial.print(TANK_INDUCTANCE_UH);
    Serial.println(F(" uH"));
    Serial.println(F("Freq (MHz)\tC (pF)"));
}

void loop() {

<<<<<<< Updated upstream:FDC2214/12x4_grid_fdc2214/12x4_grid_fdc2214.ino
    Serial.print("YO");
    for(int r = 0; r < 4; r++){
        if(r == 0){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, LOW);
        }
        else if(r == 1){
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, LOW);
        }
        else if(r == 2){
            digitalWrite(mux1_A, LOW);
            digitalWrite(mux1_B, HIGH);
        }
        else{ //r == 3
            digitalWrite(mux1_A, HIGH);
            digitalWrite(mux1_B, HIGH);
        }
        for(int c =0; c < 4; c++){
            if(c == 0){
                digitalWrite(mux2_A, LOW);
                digitalWrite(mux2_B, LOW);
            }
            else if(c == 1){
                digitalWrite(mux2_A, HIGH);
                digitalWrite(mux2_B, LOW);
            }
            else if(c == 2){
                digitalWrite(mux2_A, LOW);
                digitalWrite(mux2_B, HIGH);
            }
            else{ //r == 3
                digitalWrite(mux2_A, HIGH);
                digitalWrite(mux2_B, HIGH);
            }
=======

    for(int r = 0; r < 2; r++){
        if(r == 0){
            digitalWrite(mux1_A, LOW);
            //digitalWrite(mux1_B, LOW);
            //digitalWrite(mux1_C, LOW);
        }
        else if(r == 1){
            digitalWrite(mux1_A, HIGH);
            //digitalWrite(mux1_B, LOW);
            //digitalWrite(mux1_C, LOW);
        }
        

        for(int c =0; c < 2; c++){
        if(c == 0){
            digitalWrite(mux2_A, LOW);
            //digitalWrite(mux2_B, LOW);
            //digitalWrite(mux2_C, LOW);
        }
        else if(c == 1){
            digitalWrite(mux2_A, HIGH);
            //digitalWrite(mux2_B, LOW);
            //digitalWrite(mux2_C, LOW);
        }
        


>>>>>>> Stashed changes:FDC2214/4x4_grid_fdc2214/4x4_grid_fdc2214.ino
            Serial.print(r);
            Serial.print(",");
            Serial.print(c);
            Serial.print(": ");
            read_cap();
        }
    }
    Serial.println(' ');
    //delay(1000);
}
