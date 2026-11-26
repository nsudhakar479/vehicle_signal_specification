function create_kuksa_demo(outputDir)
if nargin < 1
    outputDir = fullfile(fileparts(mfilename('fullpath')), '..', 'generated', 'kuksa-demo');
end
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end
model = 'kuksa_v2_demo';
modelFile = fullfile(outputDir, [model '.slx']);
dictionaryFile = fullfile(outputDir, 'kuksa_v2_demo.sldd');
if exist(modelFile, 'file') || exist(dictionaryFile, 'file') || bdIsLoaded(model)
    error('KUKSA:OutputExists', 'Close the model and use a new output directory.');
end

dictionary = Simulink.data.dictionary.create(dictionaryFile);
section = getSection(dictionary, 'Design Data');
names = {'VSS_Vehicle_Speed', 'VSS_Vehicle_Speed_Valid', ...
    'VSS_ABS_IsEngaged', 'VSS_ABS_IsEngaged_Valid'};
types = {'single', 'boolean', 'boolean', 'boolean'};
descriptions = {'Vehicle.Speed', 'Vehicle.Speed value available', ...
    'Vehicle.ADAS.ABS.IsEngaged', 'Vehicle.ADAS.ABS.IsEngaged value available'};
for index = 1:numel(names)
    signal = Simulink.Signal;
    signal.DataType = types{index};
    signal.Description = descriptions{index};
    if index == 1
        signal.Unit = 'km/h';
    end
    addEntry(section, names{index}, signal);
end
saveChanges(dictionary);
close(dictionary);

addpath(outputDir);
new_system(model);
set_param(model, 'DataDictionary', 'kuksa_v2_demo.sldd', 'StopTime', '10');
block = [model '/KUKSA V2'];
add_block('simulink/User-Defined Functions/MATLAB System', block, ...
    'Position', [240 90 410 260]);
set_param(block, 'System', 'KuksaV2System');

inputs = {'ABS target', 'Send command'};
for index = 1:numel(inputs)
    inputBlock = [model '/' inputs{index}];
    y = 110 + (index - 1) * 70;
    add_block('simulink/Sources/Constant', inputBlock, ...
        'Value', 'false', 'OutDataTypeStr', 'boolean', ...
        'Position', [45 y 110 y + 30]);
    add_line(model, [inputs{index} '/1'], ['KUKSA V2/' num2str(index)]);
end

outputs = {'Speed', 'Speed valid', 'ABS engaged', 'ABS valid'};
for index = 1:numel(outputs)
    outputBlock = [model '/' outputs{index}];
    y = 70 + (index - 1) * 60;
    add_block('simulink/Ports & Subsystems/Out1', outputBlock, ...
        'Position', [550 y 580 y + 20]);
    line = add_line(model, ['KUKSA V2/' num2str(index)], [outputs{index} '/1']);
    set_param(line, 'Name', names{index});
    set_param(get_param(line, 'SrcPortHandle'), 'MustResolveToSignalObject', 'on');
end
save_system(model, modelFile);
close_system(model, 0);
fprintf('Created %s and %s\n', modelFile, dictionaryFile);
end