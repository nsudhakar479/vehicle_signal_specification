function create_tire_pressure_demo(outputDir)
if nargin < 1
    outputDir = fullfile(fileparts(mfilename('fullpath')), '..', 'generated', 'tire-pressure-demo');
end
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end
model = 'tire_pressure_demo';
modelFile = fullfile(outputDir, [model '.slx']);
dictionaryFile = fullfile(outputDir, 'tire_pressure_demo.sldd');
if exist(modelFile, 'file') || exist(dictionaryFile, 'file') || bdIsLoaded(model)
    error('TireModel:OutputExists', 'Close the model and use a new output directory.');
end

dictionary = Simulink.data.dictionary.create(dictionaryFile);
section = getSection(dictionary, 'Design Data');
names = {'VSS_FL_TirePressure','VSS_FR_TirePressure','VSS_RL_TirePressure','VSS_RR_TirePressure', ...
         'VSS_FL_IsPressureLow','VSS_FR_IsPressureLow','VSS_RL_IsPressureLow','VSS_RR_IsPressureLow'};
types = {'uint16','uint16','uint16','uint16','boolean','boolean','boolean','boolean'};
units = {'kPa','kPa','kPa','kPa','','','',''};
for index = 1:numel(names)
    signal = Simulink.Signal;
    signal.DataType = types{index};
    if ~isempty(units{index})
        signal.Unit = units{index};
    end
    signal.Description = names{index};
    addEntry(section, names{index}, signal);
end
saveChanges(dictionary); close(dictionary);

addpath(outputDir);
new_system(model);
set_param(model, 'DataDictionary', 'tire_pressure_demo.sldd', 'StopTime', '60', ...
          'EnablePacing', 'on', 'PacingRate', '1');
block = [model '/KUKSA Tire Pressure'];
add_block('simulink/User-Defined Functions/MATLAB System', block, ...
    'Position', [220 80 400 330]);
set_param(block, 'System', 'TirePressureSystem', 'Port', '55556', 'SampleTime', '1.0', ...
    'PressureDropPerSecond', '1', 'LowPressureThreshold', '210');

labels = {'FL Pressure kPa','FR Pressure kPa','RL Pressure kPa','RR Pressure kPa', ...
          'FL Low','FR Low','RL Low','RR Low'};
for index = 1:numel(labels)
    outName = [model '/' labels{index}];
    y = 60 + (index-1)*45;
    add_block('simulink/Ports & Subsystems/Out1', outName, ...
        'Position', [520 y 550 y+20]);
    line = add_line(model, ['KUKSA Tire Pressure/' num2str(index)], [labels{index} '/1']);
    set_param(line, 'Name', names{index});
    set_param(get_param(line, 'SrcPortHandle'), 'MustResolveToSignalObject', 'on');
end

save_system(model, modelFile); close_system(model, 0);
fprintf('Created %s and %s\n', modelFile, dictionaryFile);
end
