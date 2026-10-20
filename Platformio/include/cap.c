// FDC2214 raw reading -> picofarads.
//
//   f_sensor = FIN_SEL * f_REF * DATA / 2^28          (FDC2214 datasheet)
//   f_REF    = f_CLK / FREF_DIVIDER
//   C_total  = 1 / (L * (2*pi*f_sensor)^2)            (LC tank resonance)
//   C_sensor = C_total - C_FIXED
//
// !!! The values below are ASSUMPTIONS. They must match how your driver configures the
// !!! chip (CLOCK_DIVIDERS_CH0 register, clock source) and your real tank inductor.
#include "cap.h"

#define F_CLK_HZ      43400000.0   // internal oscillator, typically ~43.4 MHz (use your external clock if you have one)
#define FREF_DIVIDER  1.0          // CH0_FREF_DIVIDER from the driver's CLOCK_DIVIDERS_CH0 setting
#define FIN_SEL       1.0          // CH0_FIN_SEL: 1 for sensor freq 0.01-8.75 MHz, 2 for 5-10 MHz
#define TANK_L_UH     18.0         // tank inductor, microhenries
#define C_FIXED_PF    0.0          // fixed tank capacitor to subtract (0 = report total tank capacitance)

#define TWO_PI        6.283185307179586

double computeCap_pf(unsigned long raw) {
    raw &= 0x0FFFFFFFUL;                       // keep the 28 data bits
    if (raw == 0) return 0.0;                  // no valid reading

    double f_ref    = F_CLK_HZ / FREF_DIVIDER;
    double f_sensor = FIN_SEL * f_ref * (double)raw / 268435456.0;   // 2^28
    double w        = TWO_PI * f_sensor;
    double L        = TANK_L_UH * 1e-6;

    return (1.0 / (L * w * w)) * 1e12 - C_FIXED_PF;                  // farads -> pF
}