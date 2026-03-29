#!/usr/bin/env python3
"""JSON Patch - Apply RFC 6902 patches to JSON documents."""
import sys, json, copy

def resolve(doc, path):
    if path == "" or path == "/": return doc, None, doc
    parts = path.strip("/").split("/")
    parts = [p.replace("~1", "/").replace("~0", "~") for p in parts]
    current = doc
    for i, part in enumerate(parts[:-1]):
        if isinstance(current, list): part = int(part)
        current = current[part]
    key = parts[-1]
    if isinstance(current, list): key = int(key) if key != "-" else len(current)
    return current, key, current[key] if key != len(current) if isinstance(current, list) else False else None

def apply_op(doc, op):
    kind = op["op"]; path = op["path"]
    if kind == "add":
        parts = path.strip("/").split("/"); parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        key = parts[-1]
        if isinstance(parent, list):
            idx = len(parent) if key == "-" else int(key)
            parent.insert(idx, op["value"])
        else:
            parent[key] = op["value"]
    elif kind == "remove":
        parts = path.strip("/").split("/"); parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        key = parts[-1]
        if isinstance(parent, list): del parent[int(key)]
        else: del parent[key]
    elif kind == "replace":
        parts = path.strip("/").split("/"); parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        key = parts[-1]
        if isinstance(parent, list): parent[int(key)] = op["value"]
        else: parent[key] = op["value"]
    elif kind == "move":
        parts = op["from"].strip("/").split("/"); parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        key = parts[-1]
        if isinstance(parent, list): val = parent.pop(int(key))
        else: val = parent.pop(key)
        op2 = {"op": "add", "path": path, "value": val}
        apply_op(doc, op2)
    elif kind == "copy":
        parts = op["from"].strip("/").split("/"); current = doc
        for p in parts:
            current = current[int(p)] if isinstance(current, list) else current[p]
        apply_op(doc, {"op": "add", "path": path, "value": copy.deepcopy(current)})
    elif kind == "test":
        parts = path.strip("/").split("/"); current = doc
        for p in parts:
            current = current[int(p)] if isinstance(current, list) else current[p]
        if current != op["value"]:
            raise ValueError(f"Test failed: {path} is {current}, expected {op['value']}")
    return doc

def apply_patch(doc, patch):
    doc = copy.deepcopy(doc)
    for op in patch: doc = apply_op(doc, op)
    return doc

def main():
    if len(sys.argv) >= 3:
        with open(sys.argv[1]) as f: doc = json.load(f)
        with open(sys.argv[2]) as f: patch = json.load(f)
        result = apply_patch(doc, patch)
        print(json.dumps(result, indent=2))
    else:
        doc = {"name": "Rogue", "version": 1, "tags": ["ai", "cli"], "meta": {"lang": "python"}}
        patch = [
            {"op": "replace", "path": "/version", "value": 2},
            {"op": "add", "path": "/tags/-", "value": "tool"},
            {"op": "remove", "path": "/tags/0"},
            {"op": "add", "path": "/author", "value": "rogue-agent1"},
            {"op": "test", "path": "/name", "value": "Rogue"},
        ]
        print("=== JSON Patch (RFC 6902) ===\n")
        print(f"Original: {json.dumps(doc)}")
        print(f"Patch: {len(patch)} operations")
        result = apply_patch(doc, patch)
        print(f"Result:   {json.dumps(result)}")

if __name__ == "__main__":
    main()
