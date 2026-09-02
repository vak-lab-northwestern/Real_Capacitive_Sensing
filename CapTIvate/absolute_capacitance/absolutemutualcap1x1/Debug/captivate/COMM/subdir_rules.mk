################################################################################
# Automatically-generated file. Do not edit!
################################################################################

# Each subdirectory must supply rules for building sources it contributes
captivate/COMM/%.obj: ../captivate/COMM/%.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'MSP430 Compiler - building file: "$<"'
	"/Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS/bin/cl430" -vmspx --code_model=large --data_model=large -O3 --opt_for_speed=0 --use_hw_mpy=F5 --include_path="/Applications/ti/ccs2100/ccs/ccs_base/msp430/include" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/driverlib" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/driverlib/MSP430FR2xx_4xx" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/mathlib" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate/ADVANCED" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate/BASE" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate/COMM" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate_app" --include_path="/Users/andresturullols/workspace_ccstheia/absolutemutualcap1x1/captivate_config" --include_path="/Applications/ti/ccs2100/ccs/tools/compiler/ti-cgt-msp430_21.6.2.LTS/include" --advice:power="none" --advice:hw_config=all --define=__MSP430FR2676__ --define=_FRWP_ENABLE --define=_INFO_FRWP_ENABLE --define=TARGET_IS_MSP430FR2XX_4XX -g --gcc --printf_support=minimal --diag_warning=225 --diag_wrap=off --display_error_number --silicon_errata=CPU21 --silicon_errata=CPU22 --silicon_errata=CPU40 --preproc_with_compile --preproc_dependency="captivate/COMM/$(basename $(<F)).d_raw" --obj_directory="captivate/COMM" $(GEN_OPTS__FLAG) "$<"
	@echo 'Finished building: "$<"'
	@echo ' '


