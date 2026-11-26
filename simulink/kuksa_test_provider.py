"""Publish synthetic values and simulate ABS actuation on a local test broker."""

import argparse
import math
import queue
import threading
import time

import grpc
from kuksa.val.v2 import types_pb2, val_pb2, val_pb2_grpc


SPEED_PATH = "Vehicle.Speed"
ENGAGED_PATH = "Vehicle.ADAS.ABS.IsEngaged"
ENABLE_PATH = "Vehicle.ADAS.ABS.IsEnabled"


def publish(stub, path, value):
    stub.PublishValue(val_pb2.PublishValueRequest(
        signal_id=types_pb2.SignalID(path=path),
        data_point=types_pb2.Datapoint(value=value),
    ), timeout=3)


def run(port):
    requests = queue.Queue()
    stopped = threading.Event()
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = val_pb2_grpc.VALStub(channel)

    def request_stream():
        while True:
            request = requests.get()
            if request is None:
                return
            yield request

    requests.put(val_pb2.OpenProviderStreamRequest(
        provide_actuation_request=val_pb2.ProvideActuationRequest(
            actuator_identifiers=[types_pb2.SignalID(path=ENABLE_PATH)]
        )
    ))
    stream = stub.OpenProviderStream(request_stream())

    def feed():
        start = time.monotonic()
        try:
            while not stopped.is_set():
                speed = 40.0 + 20.0 * math.sin((time.monotonic() - start) / 5.0)
                publish(stub, SPEED_PATH, types_pb2.Value(float=speed))
                publish(stub, ENGAGED_PATH, types_pb2.Value(bool=True))
                print(f"Synthetic speed: {speed:.1f} km/h; ABS engaged: false", flush=True)
                stopped.wait(1.0)
        except grpc.RpcError as error:
            print(f"Test feed failed: {error}", flush=True)
            stream.cancel()

    feed_thread = None
    try:
        for response in stream:
            if response.HasField("provide_actuation_response"):
                print("Simulated ABS actuator registered; starting synthetic feed", flush=True)
                feed_thread = threading.Thread(target=feed, daemon=True)
                feed_thread.start()
            elif response.HasField("batch_actuate_stream_request"):
                for actuation in response.batch_actuate_stream_request.actuate_requests:
                    if actuation.value.WhichOneof("typed_value") != "bool":
                        raise ValueError("Unexpected actuator value type")
                    target = actuation.value.bool
                    publish(stub, ENABLE_PATH, types_pb2.Value(bool=target))
                    requests.put(val_pb2.OpenProviderStreamRequest(
                        batch_actuate_stream_response=val_pb2.BatchActuateStreamResponse(
                            signal_id=actuation.signal_id
                        )
                    ))
                    print(f"Simulated ABS enabled: {target}", flush=True)
    finally:
        stopped.set()
        requests.put(None)
        stream.cancel()
        if feed_thread is not None:
            feed_thread.join(timeout=4)
        channel.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=55556)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        run(args.port)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
