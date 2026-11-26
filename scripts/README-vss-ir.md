# VSS intermediate representation and mapping manifest

`vss_ir.py` converts an expanded JSON export from vss-tools into a flat,
path-addressed intermediate representation and a leaf-level mapping manifest.
It requires Python 3 and uses only the standard library.

```sh
python3 scripts/vss_ir.py /path/to/vss.json \
  --output-dir /path/to/output --vss-version 6.1
```

The output directory receives `vss_ir.json` and `mapping_manifest.json`.
Existing files with these names are overwritten. Each IR node has its full VSS
path and all exported metadata except the structural `children` field. The
manifest contains one entry per sensor, actuator, or attribute. Its Simulink
and data dictionary mappings are unassigned, and its KUKSA path is a candidate
only: the runtime server and model must be checked before using it. This tool
does not generate MATLAB artifacts or implement a runtime adapter.

A separate three-signal Simulink and KUKSA V2 prototype is documented in
[`simulink/README.md`](../simulink/README.md). It does not yet generate models
from this IR or manifest.

Both files record the SHA-256 of the exact input JSON. The version and optional
`--source-revision`, `--tools-revision`, and repeatable `--overlay` values are
user-supplied provenance, not verified claims. Overlays must be listed in the
order applied. Use `--no-overlays` only when none were applied; an omitted
overlay option records the overlay list as unknown (`null`). A version label
and JSON hash pin this input artifact, but cannot prove which VSS sources,
units, quantities, overlays, or vss-tools revision produced it. For a fully
reproducible export, retain and pin all of those inputs and the export command.
The normalizer does not run vss-tools validation; validate and export the model
with vss-tools before running it. Unexpanded instance nodes are rejected.

Run the focused tests from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_vss_ir.py'
```