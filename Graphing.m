portName = "COM4";
baudRate = 115200;
plotWindowSeconds = 60;

device = serialport(portName, baudRate);
configureTerminator(device, "LF");
flush(device);

f = figure('Name', 'Live Capacitance Plot', 'NumberTitle', 'off');
uicontrol('Style', 'pushbutton', 'String', 'Stop', ...
    'Position', [20 20 60 30], 'Callback', 'delete(gcf)');

h = animatedline;
ax = gca;
ax.YLabel.String = 'Capacitance (pF)';
ax.XLabel.String = 'Time (s)';
title('Live FDC2214 Capacitance Data');
grid on;

startTime = datetime('now');
timeData = [];
capData = [];

while ishandle(f)
    if device.NumBytesAvailable > 0
        line = readline(device);
        capVal = str2double(line);
        
        if ~isnan(capVal)
            t = seconds(datetime('now') - startTime);
            timeData(end+1) = t;
            capData(end+1) = capVal;
            addpoints(h, t, capVal);
            
            if t > plotWindowSeconds
                xlim([t - plotWindowSeconds, t]);
            end
            
            drawnow limitrate;
        end
    end
end

outputTable = table(timeData', capData', 'VariableNames', {'Time_s', 'Capacitance_pF'});
writetable(outputTable, 'fdc2214_data_log.csv');
disp("Data saved to
