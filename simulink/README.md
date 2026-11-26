# Simulink KUKSA V2 prototype

## Tire-pressure model

The tire-pressure model is a separate vehicle test experience. It uses the
`TirePressureSystem` MATLAB System block and the V2 Python bridge to publish
four tire-pressure sensors and their low-pressure flags directly through gRPC.
No external tire provider is required.

The native Windows copy and model are located at:

```text
C:\Tools\vss-tire-demo\simulink
C:\Tools\vss-tire-demo\model\tire_pressure_demo.slx
C:\Tools\vss-tire-demo\model\tire_pressure_demo.sldd
```

The model publishes these VSS paths once per second:

- `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure`
- `Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure`
- `Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure`
- `Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure`
- Their corresponding `IsPressureLow` signals

Open and run it in MATLAB:

```matlab
pyenv('Version', 'C:\temp\vss-kuksa-python-3.13.5\python.exe', ...
      'ExecutionMode', 'OutOfProcess');

addpath('C:\Tools\vss-tire-demo\simulink');
addpath('C:\Tools\vss-tire-demo\model');
rehash;

open_system('C:\Tools\vss-tire-demo\model\tire_pressure_demo.slx');
set_param('tire_pressure_demo', 'DataDictionary', 'tire_pressure_demo.sldd');
set_param('tire_pressure_demo/KUKSA Tire Pressure', ...
          'System', 'TirePressureSystem', ...
          'Host', '127.0.0.1', ...
          'Port', '55556', ...
          'Timeout', '3', ...
          'SampleTime', '1.0', ...
          'PressureDropPerSecond', '1', ...
          'LowPressureThreshold', '210');
set_param('tire_pressure_demo', 'SimulationCommand', 'update');
set_param('tire_pressure_demo', 'StopTime', 'inf', ...
          'EnablePacing', 'on', 'PacingRate', '1');
set_param('tire_pressure_demo', 'SimulationCommand', 'start');
```

Stop the model with:

```matlab
set_param('tire_pressure_demo', 'SimulationCommand', 'stop');
```

The MATLAB System block calls the KUKSA Python SDK, which uses gRPC over TCP
on `Host:Port`. This is not a plain socket or HTTP polling implementation.
Pressure starts at `220, 218, 225, 223 kPa` and decreases by 1 kPa at subsequent
one-second steps. The low-pressure flags become true below 210 kPa.

## ABS prototype

This simulation-only prototype connects three example paths to a KUKSA VAL V2
gRPC server. The model uses `KuksaV2System`, which calls the Python bridge;
the data dictionary defines the four output signal objects. The paths are
explicitly selected from the VSS export, not generated for the whole catalog.

| Path | Direction | Simulink type |
| --- | --- | --- |
| `Vehicle.Speed` | Read | `single`, km/h |
| `Vehicle.ADAS.ABS.IsEngaged` | Read | `boolean` |
| `Vehicle.ADAS.ABS.IsEnabled` | Optional actuator target | `boolean` |

## Setup

MATLAB R2026b with Simulink and a compatible 64-bit Windows Python 3.11-3.14
are required. The Python interpreter must be Windows Python because MATLAB is
running on Windows; a WSL Python environment cannot be loaded by Windows
MATLAB. Install `kuksa-client==0.6.0` into that Python environment, for example
using `python.exe -m pip install -r simulink/requirements.txt` from Windows.
Choose it in MATLAB before Python is loaded:

```matlab
pyenv('Version', 'C:\path\to\python.exe', 'ExecutionMode', 'OutOfProcess');
```

For the local test, an isolated portable Python with the dependencies was
prepared at `C:\temp\vss-kuksa-python-3.13.5\python.exe`. It is temporary;
use a maintained Python installation for ongoing work.

Add this folder and the generated model folder to the MATLAB path, then open
the existing model. For the current WSL workspace:

```matlab
root = '\\wsl.localhost\Ubuntu\home\set6kor\Raspberry\VSS\vehicle_signal_specification';
addpath(fullfile(root, 'simulink'));
addpath(fullfile(root, 'generated', 'kuksa-demo-final'));
open_system('kuksa_v2_demo');
```

To create a new model and dictionary elsewhere, call
`create_kuksa_demo('C:\path\to\new\output')`. The builder refuses to overwrite
existing artifacts. The model and dictionary must remain on the MATLAB path.

## Broker and simulation

Start a KUKSA Databroker that supports `kuksa.val.v2` and loads a compatible
VSS model containing the paths above. Configure the `KUKSA V2` block's `Host`,
`Port`, `SampleTime`, `Timeout`, and `CaFile` properties as appropriate. The
defaults are `127.0.0.1:55555`, 0.1-second sample time, and 1-second RPC
timeout. Set `KUKSA_TOKEN` in MATLAB's environment before simulation when the
broker requires a bearer token. Set `CaFile` to a trusted CA certificate to
enable TLS. Remote plaintext is rejected unless `AllowInsecureRemote` is
explicitly enabled; use that option only in a controlled test environment.

The model has `Speed`, `Speed valid`, `ABS engaged`, and `ABS valid` outputs.
An unavailable speed is `NaN`; an unavailable boolean is `false`, with its
validity output `false`. Validity means a value was present in the response,
not that it is recent. RPC errors stop the simulation rather than silently
reusing stale values. Calls are synchronous at each simulation sample, so this
is not a real-time or production control interface.

Actuation is disabled by default. With a suitable test broker and provider,
set the block's `EnableActuation` property to `true`, supply a boolean target,
and produce a rising edge on `Send command`. Each rising edge sends one V2
`Actuate` request; a request is not proof that the physical actuator moved.
Do not enable actuation on a vehicle without appropriate safety controls.

## Continuous local demonstration

For a local test broker on port 55556, a synthetic provider can generate changing
values and simulate the ABS actuator. **It writes test values to the broker and
claims the ABS actuator**, so do not run it against a vehicle or alongside a
real provider for these signals. From a WSL terminal at the repository root:

```sh
'/mnt/c/temp/vss-kuksa-python-3.13.5/python.exe' -u \
	"$(wslpath -w "$PWD/simulink/kuksa_test_provider.py")" --port 55556
```

Keep that terminal open. The provider publishes synthetic speed every second,
keeps `IsEngaged` false, and publishes the simulated `IsEnabled` state when it
receives an actuation request. These are not physical vehicle values.

Stop the model before configuring it. In MATLAB, after completing setup above:

```matlab
configure_kuksa_live('kuksa_v2_demo', 55556, true);
set_param('kuksa_v2_demo', 'SimulationCommand', 'start');
```

The model runs until stopped, at approximately real-time pace, with live
display blocks. The helper changes the open model in memory, disables output
logging for the unlimited run, and resets `Send command` to false. It does not
save the model. The third argument explicitly enables actuation; use `false` for
read-only monitoring. With a real provider, use its own security and safety
controls instead of the synthetic provider.

To request ABS enabled while the model runs:

```matlab
set_param('kuksa_v2_demo/ABS target', 'Value', 'true');
set_param('kuksa_v2_demo/Send command', 'Value', 'true');
```

Wait for `Simulated ABS enabled: True` in the provider terminal, then reset the
trigger with `set_param('kuksa_v2_demo/Send command', 'Value', 'false')`.
For another request, set the desired `ABS target` (`true` or `false`) and raise
`Send command` again. `IsEngaged` stays false in this synthetic provider; it
does not represent the actuator's enabled state. Stop the model with the
Simulink Stop button and stop the provider with Ctrl+C.

## Verification

The generated model was compiled and simulated in MATLAB R2026b against a local
mock V2 gRPC service; the optional actuator request was tested only against the
mock. The Python bridge tests require the pinned dependency:

```sh
python3 -m unittest discover -s tests -p 'test_kuksa_v2_bridge.py' -v
```

An actual broker, its VSS version, its permissions, and any actuator provider
still need to be verified in the target environment.