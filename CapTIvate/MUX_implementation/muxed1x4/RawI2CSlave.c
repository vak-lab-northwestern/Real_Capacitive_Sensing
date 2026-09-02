//*****************************************************************************
// RawI2CSlave.c
//
// See RawI2CSlave.h for the rationale (standalone, no CapTIvate dependency).
//
// Modeled on the same interrupt-driven shape as captivate/COMM/I2CSlave.c
// (START/STOP/RX/TX vectors, index/length-counted transmit buffer), but
// stripped down to what this project actually needs: read-only, single
// buffer, no length-prefix byte, no receive/error callbacks, no
// FunctionTimer-based watchdog.
//
//*****************************************************************************

#include "RawI2CSlave.h"

//*****************************************************************************
//! g_pTxBuffer/g_txLength are set by RawI2CSlave_setTransmitBuffer(); the ISR
//! serves bytes from g_pTxBuffer[0 .. g_txLength) on every fresh read,
//! restarting at index 0 on each new START condition (matching
//! captivate/COMM/I2CSlave.c's behavior — there is no register/offset
//! addressing here, same design decision as main2.c's raw port).
//*****************************************************************************
static const uint8_t *g_pTxBuffer = 0;
static volatile uint16_t g_txLength = 0;
static volatile uint16_t g_txIndex = 0;

//*****************************************************************************
//! Set true by RawI2CSlave_setTransmitBuffer() while a read of the buffer
//! currently in g_pTxBuffer might still be in progress, so a caller trying to
//! swap in a new buffer knows to wait rather than risk the ISR reading a
//! pointer that's being changed out from under it.
//*****************************************************************************
static volatile bool g_bReadInProgress = false;

void RawI2CSlave_init(void)
{
	EUSCI_B_I2C_initSlaveParam slaveParam;
	slaveParam.slaveAddress = RAWI2CSLAVE__ADDRESS;
	slaveParam.slaveAddressOffset = EUSCI_B_I2C_OWN_ADDRESS_OFFSET0;
	slaveParam.slaveOwnAddressEnable = EUSCI_B_I2C_OWN_ADDRESS_ENABLE;

	MAP_EUSCI_B_I2C_initSlave(RAWI2CSLAVE__EUSCI_B_PERIPHERAL, &slaveParam);
	MAP_EUSCI_B_I2C_enable(RAWI2CSLAVE__EUSCI_B_PERIPHERAL);

	// Enable START, STOP, RXIFG0, TXIFG0 — same four low-order interrupt
	// bits captivate/COMM/I2CSlave.c enables for eUSCI_B0 (I2CSLAVE__INT_MASK).
	MAP_EUSCI_B_I2C_clearInterrupt(RAWI2CSLAVE__EUSCI_B_PERIPHERAL, 0x0F);
	MAP_EUSCI_B_I2C_enableInterrupt(RAWI2CSLAVE__EUSCI_B_PERIPHERAL, 0x0F);

	// REQ line starts released: input (Hi-Z). It is only ever driven low,
	// never driven high, matching the open-drain convention the rest of the
	// board's REQ-style line (P1.1) already uses.
	MAP_GPIO_setAsInputPin(RAWI2CSLAVE__REQ_PORT, RAWI2CSLAVE__REQ_PIN);
}

void RawI2CSlave_setTransmitBuffer(uint8_t *pBuffer, uint16_t length)
{
	// Wait only if a read of the buffer we're about to replace might still
	// be in flight, so the pointer swap never happens mid-transfer.
	while (g_bReadInProgress) {
		__no_operation();
	}

	g_pTxBuffer = pBuffer;
	g_txLength = length;
}

void RawI2CSlave_requestRead(void)
{
	MAP_GPIO_setAsOutputPin(RAWI2CSLAVE__REQ_PORT, RAWI2CSLAVE__REQ_PIN);
	MAP_GPIO_setOutputLowOnPin(RAWI2CSLAVE__REQ_PORT, RAWI2CSLAVE__REQ_PIN);
}

#pragma vector=EUSCI_B1_VECTOR
__interrupt void RawI2CSlave_ISR(void)
{
	uint8_t ui8Data;

	switch (__even_in_range(UCB1IV, USCI_I2C_UCTXIFG0))
	{
		case USCI_I2C_UCSTTIFG:
			g_txIndex = 0;

			if (MAP_EUSCI_B_I2C_getMode(RAWI2CSLAVE__EUSCI_B_PERIPHERAL)
					== EUSCI_B_I2C_TRANSMIT_MODE)
			{
				// Master is reading from us: release REQ now (mirrors
				// captivate/COMM/I2CSlave.c releasing REQ as soon as the
				// read starts, not when it finishes), mark a read in
				// progress, and load the first byte.
				MAP_GPIO_setAsInputPin(RAWI2CSLAVE__REQ_PORT, RAWI2CSLAVE__REQ_PIN);
				g_bReadInProgress = true;

				ui8Data = (g_txIndex < g_txLength) ?
						g_pTxBuffer[g_txIndex++] : 0xFF;
				MAP_EUSCI_B_I2C_slavePutData(RAWI2CSLAVE__EUSCI_B_PERIPHERAL, ui8Data);
			}
			break;

		case USCI_I2C_UCSTPIFG:
			// Clear a possibly-pending TXIFG0, same defensive step
			// captivate/COMM/I2CSlave.c takes here for eUSCI_B0.
			UCB1IFG &= ~(UCTXIFG0);
			g_bReadInProgress = false;
			break;

		case USCI_I2C_UCRXIFG0:
			// We don't support the master writing to us, but UCBxRXBUF must
			// still be read to clear the flag — otherwise it stays asserted
			// and the ISR re-triggers continuously.
			(void)MAP_EUSCI_B_I2C_slaveGetData(RAWI2CSLAVE__EUSCI_B_PERIPHERAL);
			break;

		case USCI_I2C_UCTXIFG0:
			ui8Data = (g_txIndex < g_txLength) ?
					g_pTxBuffer[g_txIndex++] : 0xFF;
			MAP_EUSCI_B_I2C_slavePutData(RAWI2CSLAVE__EUSCI_B_PERIPHERAL, ui8Data);
			break;

		default:
			break;
	}
}
