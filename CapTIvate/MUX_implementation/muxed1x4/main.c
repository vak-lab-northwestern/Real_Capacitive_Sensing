/* --COPYRIGHT--,BSD
 * Copyright (c) 2017, Texas Instruments Incorporated
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * *  Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * *  Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * *  Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * --/COPYRIGHT--*/
//*****************************************************************************
// Development main.c for MSP430FR2676 CapTIvate devices.
//
// This starter application initializes the CapTIvate touch library
// for the touch panel specified by CAPT_UserConfig.c/.h via a call to
// CAPT_appStart(), which initializes and calibrates all sensors in the
// application, and starts the CapTIvate interval timer.
//
// Then, the capacitive touch interface is driven by calling the CapTIvate
// application handler, CAPT_appHandler().  The application handler manages
// whether the user interface (UI) is running in full active scan mode, or
// in a low-power wake-on-proximity mode.
//
// \version 1.83.00.05
// Released on May 15, 2020
//
//*****************************************************************************

#include <msp430.h>                      // Generic MSP430 Device Include
#include "driverlib.h"                   // MSPWare Driver Library
#include "captivate.h"                   // CapTIvate Touch Software Library
#include "CAPT_App.h"                    // CapTIvate Application Code
#include "CAPT_BSP.h"                    // CapTIvate EVM Board Support Package
#include "I2CSlave.h"                    // Raw I2C slave driver (CAPT_INTERFACE
                                          // must select an I2C mode for this to compile)
#include <string.h>                      // memcpy

// create own array to store expanded since CapTIvate can't hold everything
#define NUM_MUX_CHANNELS 4
uint16_t expandedRawCounts[NUM_MUX_CHANNELS][1];

// Double-buffered raw I2C publish buffers, sized to expandedRawCounts (8 bytes).
// Alternating buffers avoids handing the I2C ISR a half-updated snapshot while
// a read may still be in flight: I2CSlave_setTransmitBuffer() only guards the
// pointer swap against an in-progress read, not the memory behind a reused
// pointer.
static uint8_t g_i2cPubBufA[sizeof(expandedRawCounts)];
static uint8_t g_i2cPubBufB[sizeof(expandedRawCounts)];
static bool g_useBufA = true;

// Raw, unframed I2C slave port: no register/command byte, no length prefix,
// master never writes to us. Overrides the framed bulk-protocol port config
// that CAPT_initCommInterface() opens by default.
static const tI2CSlavePort g_rawI2CPort =
{
	.pbReceiveCallback = 0,
	.pvErrorCallback = 0,
	.pReceiveBuffer = 0,
	.ui16ReceiveBufferSize = 0,
	.bSendReadLengthFirst = false
};

void set_mux(uint8_t channel);

static void publish_expanded_raw_counts(void)
{
	uint8_t *pNext = g_useBufA ? g_i2cPubBufA : g_i2cPubBufB;
	memcpy(pNext, expandedRawCounts, sizeof(expandedRawCounts));
	g_useBufA = !g_useBufA;

	I2CSlave_setTransmitBuffer(pNext, sizeof(expandedRawCounts));
	I2CSlave_setRequestFlag();   // pulls P1.1 (REQ) low; blocks until the
	                              // master starts reading or ~2ms timeout
}

void main(void)
{
	uint8_t channel_index = 0;
	//
	// Initialize the MCU
	// BSP_configureMCU() sets up the device IO and clocking
	// The global interrupt enable is set to allow peripherals
	// to wake the MCU.
	//
	WDTCTL = WDTPW | WDTHOLD;
	BSP_configureMCU();
	__bis_SR_register(GIE);

	//
	// Start the CapTIvate application
	//
	CAPT_appStart();

	// Take over the I2C slave port with our own raw (unframed) configuration.
	// CAPT_appStart() already opened it via CAPT_initCommInterface() using
	// CapTIvate's own bulk-protocol port config; this replaces it.
	I2CSlave_openPort(&g_rawI2CPort);

	MAP_GPIO_setAsOutputPin(GPIO_PORT_P5, GPIO_PIN0);
	MAP_GPIO_setAsOutputPin(GPIO_PORT_P5, GPIO_PIN1);
	//MAP_GPIO_setAsOutputPin(GPIO_PORT_P1, GPIO_PIN0);

	//
	// Background Loop
	//
	while(1)
	{
		//
		// Run the captivate application handler.
		// Captures values without knowing that its being muxed
		CAPT_appHandler();

		//stores recently collected data into real matrix
		// currently only meausres one element per cycle so that's why 1 is hardcoded
		for (int i = 0; i < 1; i++) {
			expandedRawCounts[channel_index][i] = BTN00_E00.pRawCount[0];
		}


		__no_operation();
		set_mux(channel_index);
		
		if (channel_index >= 3) {
			channel_index = 0;
			publish_expanded_raw_counts();   // full sweep done, push fresh data
		}
		else {
			channel_index ++;
		}

		// whole new matrix has been scanned



		//
		// End of background loop iteration
		// Go to sleep if there is nothing left to do
		//
		CAPT_appSleep();
		
	} // End background loop
} // End main()

void set_mux(uint8_t channel) {
	uint8_t select0 = channel >> 0 & 0x01;
	uint8_t select1 = channel >> 1 & 0x01;

	(select0) ? MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P5, GPIO_PIN0) : MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P5, GPIO_PIN0);
	(select1) ? MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P5, GPIO_PIN1) : MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P5, GPIO_PIN1);
}