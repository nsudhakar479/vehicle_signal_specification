#!/usr/bin/env python3
"""Normalize an exported VSS JSON tree and create a mapping manifest."""

import argparse
import hashlib
import json
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def normalize(tree):
    if not isinstance(tree, dict) or not tree:
        raise ValueError("The VSS JSON must contain a nonempty root object")

    nodes = []
    paths = set()

    def visit(name, node, parent):
        if not isinstance(name, str) or not name or "." in name:
            raise ValueError(f"Invalid VSS node name: {name!r}")
        path = f"{parent}.{name}" if parent else name
        if path in paths or not isinstance(node, dict):
            raise ValueError(f"Invalid or duplicate VSS node: {path}")
        paths.add(path)
        node_type = node.get("type")
        if node_type not in {"branch", "sensor", "actuator", "attribute"}:
            raise ValueError(f"Unsupported VSS node type at {path}: {node_type!r}")
        children = node.get("children", {})
        if not isinstance(children, dict) or (node_type != "branch" and children):
            raise ValueError(f"Invalid children at {path}")
        if node_type != "branch" and not isinstance(node.get("datatype"), str):
            raise ValueError(f"Missing datatype at {path}")
        if "instances" in node:
            raise ValueError(f"Unexpanded instances at {path}; export with instances expanded")
        nodes.append({"path": path, "metadata": {key: value for key, value in node.items() if key != "children"}})
        for child_name in sorted(children):
            visit(child_name, children[child_name], path)

    for root_name in sorted(tree):
        visit(root_name, tree[root_name], "")
    return nodes


def generate(input_path, output_dir, vss_version, source_revision=None, tools_revision=None, overlays=None):
    raw = input_path.read_bytes()
    tree = json.loads(raw, object_pairs_hook=unique_object)
    nodes = normalize(tree)
    provenance = {
        "vss_version": vss_version,
        "source_revision": source_revision,
        "vss_tools_revision": tools_revision,
        "overlays": overlays,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
    }
    ir = {"schema_version": "1.0", "provenance": provenance, "nodes": nodes}
    mappings = []
    for node in nodes:
        metadata = node["metadata"]
        if metadata["type"] != "branch":
            mappings.append({
                "vss_path": node["path"],
                "vss_type": metadata["type"],
                "datatype": metadata["datatype"],
                "unit": metadata.get("unit"),
                "simulink": None,
                "data_dictionary": None,
                "kuksa_path_candidate": node["path"],
            })
    manifest = {"schema_version": "1.0", "provenance": provenance, "mappings": mappings}
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, document in (("vss_ir.json", ir), ("mapping_manifest.json", manifest)):
        (output_dir / name).write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(nodes), len(mappings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Expanded JSON exported by vss-tools")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--vss-version", required=True, help="VSS version supplied by the user")
    parser.add_argument("--source-revision", help="Source revision used to produce the export, if known")
    parser.add_argument("--tools-revision", help="vss-tools version or revision used for the export, if known")
    overlay_group = parser.add_mutually_exclusive_group()
    overlay_group.add_argument("--overlay", action="append", dest="overlays", help="Applied overlay, in order; repeatable")
    overlay_group.add_argument("--no-overlays", action="store_const", const=[], dest="overlays", help="Confirm no overlays were applied")
    args = parser.parse_args()
    try:
        node_count, mapping_count = generate(
            args.input, args.output_dir, args.vss_version, args.source_revision, args.tools_revision, args.overlays
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    print(f"Generated {node_count} nodes and {mapping_count} mappings in {args.output_dir}")


if __name__ == "__main__":
    main()