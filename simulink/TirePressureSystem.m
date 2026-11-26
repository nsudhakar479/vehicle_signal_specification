classdef TirePressureSystem < matlab.System
    properties (Nontunable)
        Host = '127.0.0.1'
        Port = 55556
        CaFile = ''
        Timeout = 1.0
        SampleTime = 1.0
        PressureDropPerSecond = 1
        LowPressureThreshold = 210
        AllowInsecureRemote = false
    end

    properties (Access = private)
        Client
        SampleCount = 0
        Pressures = [220 218 225 223]
    end

    methods (Access = protected)
        function setupImpl(obj)
            folder = fileparts(which('TirePressureSystem'));
            pythonPath = py.sys.path;
            if int64(pythonPath.count(folder)) == 0
                insert(pythonPath, int32(0), folder);
            end
            module = py.importlib.import_module('kuksa_v2_bridge');
            obj.Client = module.KuksaV2Bridge(pyargs( ...
                'host', obj.Host, 'port', int32(obj.Port), ...
                'token', getenv('KUKSA_TOKEN'), 'ca_file', obj.CaFile, ...
                'timeout', obj.Timeout, 'enable_actuation', py.bool(false), ...
                'allow_insecure_remote', py.bool(obj.AllowInsecureRemote)));
            obj.SampleCount = 0;
            obj.Pressures = [220 218 225 223];
        end

        function [p1,p2,p3,p4,l1,l2,l3,l4] = stepImpl(obj)
            obj.SampleCount = obj.SampleCount + 1;
            if obj.SampleCount > 1
                obj.Pressures = max(0, obj.Pressures - obj.PressureDropPerSecond);
            end
            pressures = uint16(obj.Pressures);
            low = obj.Pressures < obj.LowPressureThreshold;
            obj.Client.publish_tires(py.list({int32(pressures(1)),int32(pressures(2)),int32(pressures(3)),int32(pressures(4))}), ...
                py.list({py.bool(low(1)),py.bool(low(2)),py.bool(low(3)),py.bool(low(4))}));
            p1 = pressures(1); p2 = pressures(2); p3 = pressures(3); p4 = pressures(4);
            l1 = low(1); l2 = low(2); l3 = low(3); l4 = low(4);
        end

        function resetImpl(obj)
            obj.SampleCount = 0;
            obj.Pressures = [220 218 225 223];
        end

        function releaseImpl(obj)
            if ~isempty(obj.Client)
                obj.Client.close();
                obj.Client = [];
            end
        end

        function sampleTime = getSampleTimeImpl(obj)
            sampleTime = createSampleTime(obj, 'Type', 'Discrete', 'SampleTime', obj.SampleTime);
        end

        function varargout = getOutputSizeImpl(~)
            varargout = repmat({[1 1]}, 1, 8);
        end

        function varargout = getOutputDataTypeImpl(~)
            varargout = {'uint16','uint16','uint16','uint16','boolean','boolean','boolean','boolean'};
        end

        function varargout = isOutputComplexImpl(~)
            varargout = repmat({false}, 1, 8);
        end

        function varargout = isOutputFixedSizeImpl(~)
            varargout = repmat({true}, 1, 8);
        end

        function names = getOutputNamesImpl(~)
            names = ["FL Pressure kPa","FR Pressure kPa","RL Pressure kPa","RR Pressure kPa", ...
                     "FL Low","FR Low","RL Low","RR Low"];
        end
    end

    methods (Static, Access = protected)
        function mode = getSimulateUsingImpl
            mode = 'Interpreted execution';
        end
    end
end
