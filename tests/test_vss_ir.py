import json
import tempfile
import unittest
from pathlib import Path

from scripts.vss_ir import generate, normalize, unique_object


class VssIrTests(unittest.TestCase):
    def setUp(self):
        self.tree = {
            "Vehicle": {
                "type": "branch",
                "description": "Vehicle",
                "children": {
                    "Speed": {
                        "type": "sensor",
                        "datatype": "float",
                        "unit": "km/h",
                        "min": 0,
                        "allowed": [0, 10],
                        "custom": {"nested": True},
                    },
                    "Mode": {"type": "actuator", "datatype": "string"},
                },
            }
        }

    def test_metadata_and_sorted_paths_are_preserved(self):
        nodes = normalize(self.tree)
        self.assertEqual([node["path"] for node in nodes], ["Vehicle", "Vehicle.Mode", "Vehicle.Speed"])
        self.assertEqual(nodes[2]["metadata"], self.tree["Vehicle"]["children"]["Speed"])

    def test_manifest_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps(self.tree), encoding="utf-8")
            self.assertEqual(generate(source, root / "out", "6.1", overlays=[]), (3, 2))
            ir = json.loads((root / "out" / "vss_ir.json").read_text(encoding="utf-8"))
            manifest = json.loads((root / "out" / "mapping_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(ir["provenance"], manifest["provenance"])
            self.assertEqual(ir["provenance"]["overlays"], [])
            self.assertIsNone(ir["provenance"]["source_revision"])
            self.assertEqual(manifest["mappings"][1]["kuksa_path_candidate"], "Vehicle.Speed")
            self.assertIsNone(manifest["mappings"][1]["simulink"])
            first = (root / "out" / "vss_ir.json").read_bytes()
            generate(source, root / "out", "6.1", overlays=[])
            self.assertEqual(first, (root / "out" / "vss_ir.json").read_bytes())

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            json.loads('{"Vehicle": {}, "Vehicle": {}}', object_pairs_hook=unique_object)
        with self.assertRaisesRegex(ValueError, "Unexpanded instances"):
            normalize({"Vehicle": {"type": "branch", "instances": ["Left", "Right"]}})
        with self.assertRaisesRegex(ValueError, "Missing datatype"):
            normalize({"Vehicle": {"type": "sensor"}})
        with self.assertRaisesRegex(ValueError, "Invalid VSS node name"):
            normalize({"Vehicle.Speed": {"type": "sensor", "datatype": "float"}})


if __name__ == "__main__":
    unittest.main()