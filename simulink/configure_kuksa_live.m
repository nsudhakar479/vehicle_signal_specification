function configure_kuksa_live(model, port, enableActuation)
if nargin < 1
    model = 'kuksa_v2_demo';
end
if nargin < 2
    port = 55556;
end
if nargin < 3
    enableActuation = false;
end
validateattributes(port, {'numeric'}, {'scalar', 'integer', '>=', 1, '<=', 65535});
validateattributes(enableActuation, {'logical'}, {'scalar'});
load_system(model);
if ~strcmp(get_param(model, 'SimulationStatus'), 'stopped')
    error('KUKSA:ModelRunning', 'Stop the model before configuring live mode.');
end

block = [model '/KUKSA V2'];
if enableActuation
    actuationSetting = 'true';
else
    actuationSetting = 'false';
end
set_param(block, 'Port', num2str(port), 'Timeout', '3', 'EnableActuation', actuationSetting);
set_param([model '/Send command'], 'Value', 'false');
set_param(model, 'StopTime', 'inf', 'EnablePacing', 'on', 'PacingRate', '1', ...
    'SaveTime', 'off', 'SaveOutput', 'off', 'SignalLogging', 'off');

names = {'Live Speed kmh', 'Live Speed Valid', 'Live ABS Engaged', 'Live ABS Valid'};
for index = 1:numel(names)
    displayBlock = [model '/' names{index}];
    if getSimulinkBlockHandle(displayBlock) == -1
        y = 320 + (index - 1) * 55;
        add_block('simulink/Sinks/Display', displayBlock, ...
            'Position', [550 y 640 y + 30]);
        add_line(model, ['KUKSA V2/' num2str(index)], [names{index} '/1'], ...
            'autorouting', 'on');
    end
end
end