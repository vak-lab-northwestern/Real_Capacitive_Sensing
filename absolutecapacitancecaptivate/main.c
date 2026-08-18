//currently not working!!
// needs more work


/*
Calculates base electrode capacitance for mutual capacitance grids, should work for any size grid
for example, 1x1, 2x2, 4x4, 5x5, 5x4, 7x7, etc...

How to use:
- Create project in CapTIvate Design center with desired sensor size, generate source code in Code Composer Studio
- Copy this code into main.c, and change num_elements
- Run while connected via USB to MSP430 board, run debug mode to check values in base_electrode_capacitance[]
*/

#include <msp430.h>                      // Generic MSP430 Device Include
#include "driverlib.h"                   // MSPWare Driver Library
#include "captivate.h"                   // CapTIvate Touch Software Library
#include "CAPT_App.h"                    // CapTIvate Application Code
#include "CAPT_BSP.h"                    // CapTIvate EVM Board Support Package

//16 elements for 4x4 grid
#define num_elements 16

//hold "counts" -> amount of transfers necessary to fill up internal sample capacitor
volatile uint16_t raw[num_elements];
volatile uint16_t rawRefCap[num_elements];

volatile float percent_change_capacitance[num_elements];
volatile float base_electrode_capacitance[num_elements];

void main(void)
{
	uint8_t num_cycles;
    uint8_t num_elem_per_cycle;
    int elem_index;
    int i;
    int j;
    tElement* pElem;
	//
	// Initialize the MCU
	// BSP_configureMCU() sets up the device IO and clocking
	// The global interrupt enable is set to allow peripherals
	// to wake the MCU.
	//
	WDTCTL = WDTPW | WDTHOLD;
	BSP_configureMCU();
	__bis_SR_register(GIE);

	// Start the CapTIvate application, roughly same as CAP_appstart()
    CAPT_initUI(&g_uiApp);
    CAPT_calibrateUI(&g_uiApp);

	//loop through all cycles in sensor, nexted loop through elements in each cyle.
	//calculate find baseline electrode capacitance for all elements
	
	num_cycles = BTN00.ui8NrOfCycles;
	elem_index = 0;
	for (i = 0; i<num_cycles; i++) {
		num_elem_per_cycle = BTN00.pCycle[i]->ui8NrOfElements;
		for (j = 0; j<num_elem_per_cycle; j++) {
			
			//get pointer to desired element
			pElem = BTN00.pCycle[i]->pElements[j];
			
			//update sensor readings, store in raw array
			CAPT_updateSensor(&BTN00, g_uiApp.ui8AppLPM);
			raw[elem_index] = pElem->pRawCount[0]; 

			//enable 0.5 pF reference capacitor by passing '1'
			CAPT_enableRefCap(pElem,1);

			//update sensor readings to include ref cap, store in rawRefCap array
			CAPT_updateSensor(&BTN00, g_uiApp.ui8AppLPM);
			rawRefCap[elem_index] = pElem->pRawCount[0];

			//calculate and store base_electrode_capacitance in picofarads
			percent_change_capacitance[elem_index] = 100.0f * (1.0f/rawRefCap[elem_index] - 1.0f/raw[elem_index]) * 100.0f;
			base_electrode_capacitance[elem_index] = 0.5f / (percent_change_capacitance[elem_index]/100.0f);
			
			MAP_CAPT_disableRefCap();
			//move on to next element
			elem_index++;
		}
	}
	//when done, freeze program
	while(1);
} // End main()

