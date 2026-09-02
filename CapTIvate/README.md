Code for using CapTIvate on MSP430FR2676 for Capacitive Sensing Applications

Contents:
- bulk_I2C_source_code/
    - flash MSP430 with these programs if you want to view capacitance within CapTIvateDesignCenter (not recommended)
- register_I2C_source_cde/
    - flash MSP430 with these programs if you want to extract capacitance data from MSP430 to external boards
- I2C_master_scripts/
    - flash ESP32 with these scripts to read capacitive count data from MSP430 in register_I2C mode
    - ESP32 prints data out in Serial CSV format
- python_logging_scripts/
    - take CSV format count data and log
- python_visualization_scripts/
    - take CSV format count data and create heatmap visualization
- absolute_capacitance/
    - preliminary implementations of calculating absolute capacitance of electrodes
    - works once, but doesn't run continously
- MUX_implementation/
    - Very preliminary idea of how MUXes would be implemented with CapTIvate
    - Hard part would be sending I2C data to "outside world"