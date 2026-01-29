#pragma once

#include <math.h>

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