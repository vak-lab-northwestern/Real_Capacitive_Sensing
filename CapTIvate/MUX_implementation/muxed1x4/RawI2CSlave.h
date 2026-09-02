//*****************************************************************************
// RawI2CSlave.h
//
// Standalone eUSCI_B I2C slave driver, deliberately independent of the
// CapTIvate library:
//   - does not live under captivate/
//   - is not gated by CAPT_INTERFACE / CAPT_CommConfig.h (compiles
//     unconditionally, regardless of what the CapTIvate comm stack is set to)
//   - does not use CapTIvate's FunctionTimer module or any of its buffers
//   - uses eUSCI_B1, a different physical peripheral instance than
//     captivate/COMM/I2CSlave.c's eUSCI_B0, so the two can coexist without
//     resource conflicts
//
// This is a read-only slave: it only serves whatever buffer you hand it via
// RawI2CSlave_setTransmitBuffer(). It does not support the master writing to
// it (see main2.c conversation for why this project doesn't need that).
//
// NOT included, unlike captivate/COMM/I2CSlave.c's REQ mechanism:
//   - No timeout/watchdog on the REQ line. If nothing ever reads after
//     RawI2CSlave_requestRead() is called, REQ just stays low until the next
//     call. CapTIvate's I2CSlave_setRequestFlag() self-heals via a
//     FunctionTimer-based 2ms timer; reproducing that here would mean taking
//     on a Timer_A dependency, which defeats the point of this file. Add
//     your own timer-based watchdog if that guarantee matters for you.
//
//*****************************************************************************

#ifndef RAWI2CSLAVE_H_
#define RAWI2CSLAVE_H_

#include <stdint.h>
#include "driverlib.h"

//*****************************************************************************
// TODO (hardware-specific — fill in before wiring this up):
//
// Confirm which physical pins carry UCB1SDA / UCB1SCL on the MSP430FR2676
// from the device datasheet's pin-function table. That mapping is not
// derivable from anything in this repo. Once confirmed, add the matching
// PxSEL0/PxSEL1 bits in BSP_configureMCU() (captivate_app/CAPT_BSP.c) for
// those two pins, the same way P1.2/P1.3 are muxed to UCB0 today
// (CAPT_BSP.c:66-67, 74).
//
// RAWI2CSLAVE__REQ_PORT/PIN below is a plain GPIO of your choosing for the
// optional data-ready line — confirm it's free before use. Per CAPT_BSP.c,
// most of P2-P6 are currently just generic unused outputs, but pick and
// verify a specific pin rather than trusting this default blindly.
//*****************************************************************************
#define RAWI2CSLAVE__EUSCI_B_PERIPHERAL    (EUSCI_B1_BASE)
#define RAWI2CSLAVE__ADDRESS               (0x0B)   // 7-bit; must differ from
                                                      // I2CSLAVE__ADDRESS (0x0A)
                                                      // if ever on the same bus

#define RAWI2CSLAVE__REQ_PORT              (GPIO_PORT_P2)   // TODO: confirm free pin
#define RAWI2CSLAVE__REQ_PIN               (GPIO_PIN3)      // TODO: confirm free pin

//*****************************************************************************
//! Configures and enables the eUSCI_B1 peripheral as an I2C slave at
//! RAWI2CSLAVE__ADDRESS, and initializes the REQ line to its released
//! (input/Hi-Z) state. Call once at startup.
//*****************************************************************************
extern void RawI2CSlave_init(void);

//*****************************************************************************
//! Publishes a new buffer for the master to read. Blocks briefly only if a
//! read of the *previous* buffer is still in progress, to avoid swapping the
//! pointer mid-transfer — it does not wait for a read to start or finish
//! otherwise.
//!
//! \param pBuffer pointer to the data to serve on the next read(s). Must
//! remain valid/unmodified until superseded by another call to this
//! function — double-buffer at the call site if you need to keep updating
//! the source data concurrently (see main2.c's g_i2cPubBufA/B pattern).
//! \param length number of bytes available at pBuffer.
//*****************************************************************************
extern void RawI2CSlave_setTransmitBuffer(uint8_t *pBuffer, uint16_t length);

//*****************************************************************************
//! Pulls the REQ line (RAWI2CSLAVE__REQ_PORT/PIN) low to signal the master
//! that fresh data is ready. Non-blocking: returns immediately. The ISR
//! releases the line back to Hi-Z the instant it sees the master's START
//! condition begin a read. No timeout — see the NOT-included note above.
//*****************************************************************************
extern void RawI2CSlave_requestRead(void);

#endif /* RAWI2CSLAVE_H_ */
