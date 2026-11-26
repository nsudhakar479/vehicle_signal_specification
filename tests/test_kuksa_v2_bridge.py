import math
import unittest
from concurrent import futures

try:
    import grpc
    from kuksa.val.v2 import types_pb2, val_pb2, val_pb2_grpc
    from simulink.kuksa_v2_bridge import KuksaV2Bridge
except ImportError:
    grpc = None


@unittest.skipIf(grpc is None, "kuksa-client is not installed")
class KuksaV2BridgeTests(unittest.TestCase):
    def setUp(self):
        test = self

        class Broker(val_pb2_grpc.VALServicer):
            def GetValues(self, request, context):
                test.paths = [signal.path for signal in request.signal_ids]
                test.metadata = dict(context.invocation_metadata())
                return val_pb2.GetValuesResponse(data_points=test.datapoints)

            def PublishValue(self, request, context):
                test.requests.append(request)
                return val_pb2.PublishValueResponse()

            def Actuate(self, request, context):
                test.requests.append(request)
                return val_pb2.ActuateResponse()

        self.datapoints = [
            types_pb2.Datapoint(value=types_pb2.Value(float=42.5)),
            types_pb2.Datapoint(value=types_pb2.Value(bool=True)),
        ]
        self.requests = []
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        val_pb2_grpc.add_VALServicer_to_server(Broker(), self.server)
        port = self.server.add_insecure_port('127.0.0.1:0')
        self.server.start()
        self.client = KuksaV2Bridge(port=port, token='test-token')

    def tearDown(self):
        self.client.close()
        self.server.stop(0).wait()

    def test_reads_values_and_authorization_over_v2(self):
        self.assertEqual(self.client.read(), (42.5, True, True, True))
        self.assertEqual(self.paths, ['Vehicle.Speed', 'Vehicle.ADAS.ABS.IsEngaged'])
        self.assertEqual(self.metadata['authorization'], 'Bearer test-token')

    def test_unavailable_values_and_invalid_type(self):
        self.datapoints = [types_pb2.Datapoint(), types_pb2.Datapoint()]
        speed, speed_valid, engaged, engaged_valid = self.client.read()
        self.assertTrue(math.isnan(speed))
        self.assertEqual((speed_valid, engaged, engaged_valid), (False, False, False))
        self.datapoints[0] = types_pb2.Datapoint(value=types_pb2.Value(bool=True))
        with self.assertRaisesRegex(ValueError, 'expected float'):
            self.client.read()

    def test_actuation_requires_opt_in(self):
        with self.assertRaises(PermissionError):
            self.client.actuate(True)
        self.assertEqual(self.requests, [])
        self.client.enable_actuation = True
        self.client.actuate(True)
        self.assertEqual(self.requests[0].signal_id.path, 'Vehicle.ADAS.ABS.IsEnabled')
        self.assertTrue(self.requests[0].value.bool)
        with self.assertRaises(TypeError):
            self.client.actuate(1)

    def test_publish_four_tire_pressures_and_low_flags(self):
        self.client.publish_tires([221, 219, 226, 224], [False, False, False, False])
        self.assertEqual(len(self.requests), 8)
        self.assertEqual(self.requests[0].signal_id.path, 'Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure')
        self.assertEqual(self.requests[0].data_point.value.uint32, 221)

    def test_reads_four_tire_pressures_and_low_flags(self):
        self.datapoints = [
            types_pb2.Datapoint(value=types_pb2.Value(uint32=220)),
            types_pb2.Datapoint(value=types_pb2.Value(uint32=218)),
            types_pb2.Datapoint(value=types_pb2.Value(uint32=225)),
            types_pb2.Datapoint(value=types_pb2.Value(uint32=223)),
            types_pb2.Datapoint(value=types_pb2.Value(bool=False)),
            types_pb2.Datapoint(value=types_pb2.Value(bool=False)),
            types_pb2.Datapoint(value=types_pb2.Value(bool=True)),
            types_pb2.Datapoint(value=types_pb2.Value(bool=False)),
        ]
        result = self.client.read_tires()
        self.assertEqual(result, (220, 218, 225, 223, False, False, True, False))

    def test_remote_insecure_requires_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'require TLS'):
            KuksaV2Bridge(host='192.0.2.1')


if __name__ == '__main__':
    unittest.main()