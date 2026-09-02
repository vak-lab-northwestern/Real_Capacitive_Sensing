################################################################################
# Automatically-generated file. Do not edit!
################################################################################

CG_TOOL_ROOT := /Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS

GEN_OPTS__FLAG := 
GEN_CMDS__FLAG := 

ORDERED_OBJS += \
"./main.obj" \
"./captivate/ADVANCED/CAPT_Manager.obj" \
"./captivate/BASE/CAPT_ISR.obj" \
"./captivate/COMM/CAPT_Interface.obj" \
"./captivate/COMM/FunctionTimer.obj" \
"./captivate/COMM/I2CSlave.obj" \
"./captivate/COMM/UART.obj" \
"./captivate_app/CAPT_App.obj" \
"./captivate_app/CAPT_BSP.obj" \
"./captivate_config/CAPT_UserConfig.obj" \
"../lnk_msp430fr2676.cmd" \
"../captivate/BASE/libraries/captivate_fr2676_family.lib" \
"../driverlib/MSP430FR2xx_4xx/libraries/driverlib_fr2676_family.lib" \
"../mathlib/libraries/IQmathLib.lib" \
"../mathlib/libraries/IQmathLib_CCS_MPY32_5xx_6xx_CPUX_large_code_large_data.lib" \
"../mathlib/libraries/QmathLib.lib" \
"../mathlib/libraries/QmathLib_CCS_MPY32_5xx_6xx_CPUX_large_code_large_data.lib" \
$(GEN_CMDS__FLAG) \
-lfrwp_init.a \
-l"/Users/andresturullols/workspace_ccstheia/absolutemutualcap4x4/captivate/BASE/libraries/captivate_fr2676_family.lib" \
-l"/Users/andresturullols/workspace_ccstheia/absolutemutualcap4x4/driverlib/MSP430FR2xx_4xx/libraries/driverlib_fr2676_family.lib" \
-l"/Users/andresturullols/workspace_ccstheia/absolutemutualcap4x4/mathlib/libraries/QmathLib.lib" \
-l"/Users/andresturullols/workspace_ccstheia/absolutemutualcap4x4/mathlib/libraries/IQmathLib.lib" \
-llibc.a \

-include ../makefile.init

RM := rm -rf
RMDIR := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include subdir_vars.mk
-include captivate/ADVANCED/subdir_vars.mk
-include captivate/BASE/subdir_vars.mk
-include captivate/BASE/libraries/subdir_vars.mk
-include captivate/COMM/subdir_vars.mk
-include captivate_app/subdir_vars.mk
-include captivate_config/subdir_vars.mk
-include driverlib/MSP430FR2xx_4xx/libraries/subdir_vars.mk
-include mathlib/libraries/subdir_vars.mk
-include subdir_rules.mk
-include captivate/ADVANCED/subdir_rules.mk
-include captivate/BASE/subdir_rules.mk
-include captivate/BASE/libraries/subdir_rules.mk
-include captivate/COMM/subdir_rules.mk
-include captivate_app/subdir_rules.mk
-include captivate_config/subdir_rules.mk
-include driverlib/MSP430FR2xx_4xx/libraries/subdir_rules.mk
-include mathlib/libraries/subdir_rules.mk
-include objects.mk

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(C55_DEPS)),)
-include $(C55_DEPS)
endif
ifneq ($(strip $(C_UPPER_DEPS)),)
-include $(C_UPPER_DEPS)
endif
ifneq ($(strip $(S67_DEPS)),)
-include $(S67_DEPS)
endif
ifneq ($(strip $(S62_DEPS)),)
-include $(S62_DEPS)
endif
ifneq ($(strip $(S_DEPS)),)
-include $(S_DEPS)
endif
ifneq ($(strip $(OPT_DEPS)),)
-include $(OPT_DEPS)
endif
ifneq ($(strip $(C??_DEPS)),)
-include $(C??_DEPS)
endif
ifneq ($(strip $(ASM_UPPER_DEPS)),)
-include $(ASM_UPPER_DEPS)
endif
ifneq ($(strip $(S??_DEPS)),)
-include $(S??_DEPS)
endif
ifneq ($(strip $(C64_DEPS)),)
-include $(C64_DEPS)
endif
ifneq ($(strip $(CXX_DEPS)),)
-include $(CXX_DEPS)
endif
ifneq ($(strip $(S64_DEPS)),)
-include $(S64_DEPS)
endif
ifneq ($(strip $(CLA_DEPS)),)
-include $(CLA_DEPS)
endif
ifneq ($(strip $(S55_DEPS)),)
-include $(S55_DEPS)
endif
ifneq ($(strip $(SV7A_DEPS)),)
-include $(SV7A_DEPS)
endif
ifneq ($(strip $(C62_DEPS)),)
-include $(C62_DEPS)
endif
ifneq ($(strip $(C67_DEPS)),)
-include $(C67_DEPS)
endif
ifneq ($(strip $(K_DEPS)),)
-include $(K_DEPS)
endif
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
ifneq ($(strip $(CC_DEPS)),)
-include $(CC_DEPS)
endif
ifneq ($(strip $(C++_DEPS)),)
-include $(C++_DEPS)
endif
ifneq ($(strip $(C43_DEPS)),)
-include $(C43_DEPS)
endif
ifneq ($(strip $(S43_DEPS)),)
-include $(S43_DEPS)
endif
ifneq ($(strip $(ASM_DEPS)),)
-include $(ASM_DEPS)
endif
ifneq ($(strip $(S_UPPER_DEPS)),)
-include $(S_UPPER_DEPS)
endif
ifneq ($(strip $(CPP_DEPS)),)
-include $(CPP_DEPS)
endif
ifneq ($(strip $(SA_DEPS)),)
-include $(SA_DEPS)
endif
endif

-include ../makefile.defs

# Add inputs and outputs from these tool invocations to the build variables 
EXE_OUTPUTS += \
absolutemutualcap4x4.out 

EXE_OUTPUTS__QUOTED += \
"absolutemutualcap4x4.out" 


# All Target
all: $(OBJS) $(CMD_SRCS) $(LIB_SRCS) $(GEN_CMDS)
	@$(MAKE) --no-print-directory -Onone "absolutemutualcap4x4.out"

# Tool invocations
absolutemutualcap4x4.out: $(OBJS) $(CMD_SRCS) $(LIB_SRCS) $(GEN_CMDS)
	@echo 'MSP430 Linker - building target: "$@"'
	"/Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS/bin/cl430" -vmspx --code_model=large --data_model=large -O3 --opt_for_speed=0 --use_hw_mpy=F5 --advice:power="none" --advice:hw_config=all --define=__MSP430FR2676__ --define=_FRWP_ENABLE --define=_INFO_FRWP_ENABLE --define=TARGET_IS_MSP430FR2XX_4XX -g --gcc --printf_support=minimal --diag_warning=225 --diag_wrap=off --display_error_number --silicon_errata=CPU21 --silicon_errata=CPU22 --silicon_errata=CPU40 -z -m"absolutemutualcap4x4.map" --heap_size=160 --stack_size=256 --cinit_hold_wdt=on -i"/Applications/ti/ccs2100/ccs/ccs_base/msp430/include" -i"/Applications/ti/ccs2100/ccs/ccs_base/msp430/lib/FR2xx" -i"/Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS/lib" -i"/Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS/include" --priority --reread_libs --define=_FRWP_ENABLE --define=_INFO_FRWP_ENABLE --diag_wrap=off --display_error_number --warn_sections --xml_link_info="absolutemutualcap4x4_linkInfo.xml" --use_hw_mpy=F5 --rom_model -o "absolutemutualcap4x4.out" $(ORDERED_OBJS)
	@echo 'Finished building target: "$@"'
	@echo ' '

# Other Targets
clean:
	-$(RM) $(EXE_OUTPUTS__QUOTED)
	-$(RM) "main.obj" "captivate/ADVANCED/CAPT_Manager.obj" "captivate/BASE/CAPT_ISR.obj" "captivate/COMM/CAPT_Interface.obj" "captivate/COMM/FunctionTimer.obj" "captivate/COMM/I2CSlave.obj" "captivate/COMM/UART.obj" "captivate_app/CAPT_App.obj" "captivate_app/CAPT_BSP.obj" "captivate_config/CAPT_UserConfig.obj" 
	-$(RM) "main.d" "captivate/ADVANCED/CAPT_Manager.d" "captivate/BASE/CAPT_ISR.d" "captivate/COMM/CAPT_Interface.d" "captivate/COMM/FunctionTimer.d" "captivate/COMM/I2CSlave.d" "captivate/COMM/UART.d" "captivate_app/CAPT_App.d" "captivate_app/CAPT_BSP.d" "captivate_config/CAPT_UserConfig.d" 
	-@echo ' '

.PHONY: all clean dependents
.SECONDARY:

-include ../makefile.targets

