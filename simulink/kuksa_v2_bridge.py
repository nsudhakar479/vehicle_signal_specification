"""Simulation-only KUKSA VAL V2 bridge for the three-signal example."""

import ipaddress
import math
from pathlib import Path

import grpc
from kuksa.val.v2 import types_pb2, val_pb2, val_pb2_grpc


SPEED_PATH = "Vehicle.Speed"
ENGAGED_PATH = "Vehicle.ADAS.ABS.IsEngaged"
ENABLE_PATH = "Vehicle.ADAS.ABS.IsEnabled"


class KuksaV2Bridge:
    def __init__(
        self, host="127.0.0.1", port=55555, token="", ca_file="", timeout=1.0,
        enable_actuation=False, allow_insecure_remote=False,
    ):
        if not host or not 1 <= int(port) <= 65535 or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Invalid KUKSA host, port, or timeout")
        self.timeout = float(timeout)
        self.enable_actuation = bool(enable_actuation)
        self.metadata = (("authorization", f"Bearer {token}"),) if token else ()
        target = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
        if ca_file:
            credentials = grpc.ssl_channel_credentials(root_certificates=Path(ca_file).read_bytes())
            self.channel = grpc.secure_channel(target, credentials)
        else:
            try:
                is_local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_local = host.lower() == "localhost"
            if not is_local and not allow_insecure_remote:
                raise ValueError("Remote connections require TLS unless explicitly allowed")
            self.channel = grpc.insecure_channel(target)
        self.stub = val_pb2_grpc.VALStub(self.channel)

    def read(self):
        request = val_pb2.GetValuesRequest(signal_ids=[
            types_pb2.SignalID(path=SPEED_PATH),
            types_pb2.SignalID(path=ENGAGED_PATH),
        ])
        response = self.stub.GetValues(request, timeout=self.timeout, metadata=self.metadata)
        if len(response.data_points) != 2:
            raise ValueError("KUKSA returned an unexpected number of datapoints")
        speed, speed_valid = self._value(response.data_points[0], "float", math.nan)
        engaged, engaged_valid = self._value(response.data_points[1], "bool", False)
        return (speed, speed_valid, engaged, engaged_valid)

    @staticmethod
    def _value(datapoint, expected_type, unavailable):
        fields = datapoint.value.ListFields()
        if not fields:
            return unavailable, False
        if len(fields) != 1 or fields[0][0].name != expected_type:
            raise ValueError(f"Unexpected KUKSA value type, expected {expected_type}")
        return fields[0][1], True

    def actuate(self, value):
        if not self.enable_actuation:
            raise PermissionError("Actuation is disabled")
        if not isinstance(value, bool):
            raise TypeError("ABS enable target must be boolean")
        request = val_pb2.ActuateRequest(
            signal_id=types_pb2.SignalID(path=ENABLE_PATH),
            value=types_pb2.Value(bool=value),
        )
        self.stub.Actuate(request, timeout=self.timeout, metadata=self.metadata)

    def close(self):
        self.channel.close()