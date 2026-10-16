Platformio is a popular platform to use in embedded systems, giving more control back to the programmer compared to Arduino. 

The main folders are include, lib, src, scripts, and test

include:
this folder contains header (.h) files which are used to define functions, structs, and constants. any .h file can be referenced in a .cpp file by writing "#include xxx.h" and that will allow you to reference everything defined in that header file.


lib:
this folder contains libraries used. Libraries are collections of files created for the general use of a system or component that is often provided by the manufacturer and soemtimes created by individuals that had to do it themselves. Libraries can be for a wide range of areas, such as computer vision, robotics, or just individual components. In all applciations, libraries allow you to use functions without creating them yourself.

In the case of embedded systems, libraries provide you with functions that are expected for a given component, and implement it for you without you needed to go through a datasheet and understand how to implement everything at the base level. For example, a library for our capacitive sensing chip (FDC2214) allows us to simply read its values by calling fdc.getReading28()


src:
this is where the main project cpp files go. The bulk of the implementation and execution happens in these files. For our case since we have various applications we are aiming to accomplish there will be different folders within src. One of which will be for printing capacitance values for a 6x6 or 8x8 grid over UART to be visualized with a python script. Another project may be for a finger path and visualizing that differently. 


scripts:
this is where python files go. a script is _. an example is our script to read the data gathered for an 8x8 patch and visualizing it with a heatmap.


test:
not really sure honestly, havent used it yet