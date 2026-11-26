classdef KuksaV2System < matlab.System
    properties (Nontunable)
        Host = '127.0.0.1'
        Port = 55555
        CaFile = ''
        Timeout = 1.0
        SampleTime = 0.1
        EnableActuation = false
        AllowInsecureRemote = false
    end

    properties (Access = private)
        Client
        PreviousSend = false
    end

    methods (Access = protected)
        function setupImpl(obj)
            folder = fileparts(which('KuksaV2System'));
            pythonPath = py.sys.path;
            if int64(pythonPath.count(folder)) == 0
                insert(pythonPath, int32(0), folder);
            end
            module = py.importlib.import_module('kuksa_v2_bridge');
            obj.Client = module.KuksaV2Bridge(pyargs( ...
                'host', obj.Host, 'port', int32(obj.Port), ...
                'token', getenv('KUKSA_TOKEN'), 'ca_file', obj.CaFile, ...
                'timeout', obj.Timeout, 'enable_actuation', py.bool(obj.EnableActuation), ...
                'allow_insecure_remote', py.bool(obj.AllowInsecureRemote)));
            obj.PreviousSend = false;
        end

        function [speed, speedValid, engaged, engagedValid] = stepImpl(obj, target, send)
            values = obj.Client.read();
            speed = single(double(values{1}));
            speedValid = logical(values{2});
            engaged = logical(values{3});
            engagedValid = logical(values{4});
            if send && ~obj.PreviousSend
                obj.Client.actuate(py.bool(target));
            end
            obj.PreviousSend = send;
        end

        function resetImpl(obj)
            obj.PreviousSend = false;
        end

        function releaseImpl(obj)
            if ~isempty(obj.Client)
                obj.Client.close();
                obj.Client = [];
            end
        end

        function validateInputsImpl(~, target, send)
            validateattributes(target, {'logical'}, {'scalar'});
            validateattributes(send, {'logical'}, {'scalar'});
        end

        function sampleTime = getSampleTimeImpl(obj)
            sampleTime = createSampleTime(obj, 'Type', 'Discrete', 'SampleTime', obj.SampleTime);
        end

        function [a, b, c, d] = getOutputSizeImpl(~)
            a = [1 1]; b = [1 1]; c = [1 1]; d = [1 1];
        end

        function [a, b, c, d] = getOutputDataTypeImpl(~)
            a = 'single'; b = 'logical'; c = 'logical'; d = 'logical';
        end

        function [a, b, c, d] = isOutputComplexImpl(~)
            a = false; b = false; c = false; d = false;
        end

        function [a, b, c, d] = isOutputFixedSizeImpl(~)
            a = true; b = true; c = true; d = true;
        end

        function [a, b] = getInputNamesImpl(~)
            a = 'ABS target'; b = 'Send';
        end

        function [a, b, c, d] = getOutputNamesImpl(~)
            a = 'Speed km/h'; b = 'Speed valid'; c = 'ABS engaged'; d = 'ABS valid';
        end
    end

    methods (Static, Access = protected)
        function mode = getSimulateUsingImpl
            mode = 'Interpreted execution';
        end
    end
end