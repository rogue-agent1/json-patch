#!/usr/bin/env python3
"""JSON Patch (RFC 6902) implementation."""
import copy, json

def _resolve(doc, path):
    if path == "": return doc, None, None
    parts = path.lstrip("/").split("/")
    current = doc
    for i, part in enumerate(parts[:-1]):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list): part = int(part)
        current = current[part]
    last = parts[-1].replace("~1", "/").replace("~0", "~")
    if isinstance(current, list): last = int(last)
    return current, last, current[last] if last != "-" else None

def apply_patch(doc, patch):
    doc = copy.deepcopy(doc)
    for op in patch:
        operation = op["op"]
        path = op.get("path", "")
        if operation == "add":
            parts = path.lstrip("/").split("/")
            if len(parts) == 1:
                # Top-level key
                last = parts[0].replace("~1", "/").replace("~0", "~")
                if isinstance(doc, list):
                    if last == "-": doc.append(op["value"])
                    else: doc.insert(int(last), op["value"])
                else:
                    doc[last] = op["value"]
            else:
                # Navigate to parent
                parent = doc
                for p in parts[:-1]:
                    p = p.replace("~1", "/").replace("~0", "~")
                    if isinstance(parent, list): p = int(p)
                    parent = parent[p]
                last = parts[-1].replace("~1", "/").replace("~0", "~")
                if isinstance(parent, list):
                    if last == "-": parent.append(op["value"])
                    else: parent.insert(int(last), op["value"])
                else:
                    parent[last] = op["value"]
        elif operation == "remove":
            parent, key, _ = _resolve(doc, "/".join(path.split("/")[:-1]) or "")
            last = path.split("/")[-1].replace("~1", "/").replace("~0", "~")
            if isinstance(parent, list): parent.pop(int(last))
            else: del parent[last]
        elif operation == "replace":
            parent, key, _ = _resolve(doc, "/".join(path.split("/")[:-1]) or "")
            last = path.split("/")[-1].replace("~1", "/").replace("~0", "~")
            if isinstance(parent, list): parent[int(last)] = op["value"]
            else: parent[last] = op["value"]
        elif operation == "move":
            _, _, val = _resolve(doc, op["from"])
            doc = apply_patch(doc, [{"op": "remove", "path": op["from"]}])
            doc = apply_patch(doc, [{"op": "add", "path": path, "value": val}])
        elif operation == "copy":
            _, _, val = _resolve(doc, op["from"])
            doc = apply_patch(doc, [{"op": "add", "path": path, "value": copy.deepcopy(val)}])
        elif operation == "test":
            _, _, val = _resolve(doc, path)
            if val != op["value"]:
                raise ValueError(f"Test failed: {path} is {val}, expected {op['value']}")
    return doc

if __name__ == "__main__":
    doc = {"name": "test", "tags": ["a"]}
    patch = [{"op": "add", "path": "/tags/-", "value": "b"}, {"op": "replace", "path": "/name", "value": "updated"}]
    print(json.dumps(apply_patch(doc, patch), indent=2))

def test():
    doc = {"a": 1, "b": {"c": 2}, "d": [1, 2, 3]}
    # Add
    r = apply_patch(doc, [{"op": "add", "path": "/e", "value": 4}])
    assert r["e"] == 4
    # Replace
    r = apply_patch(doc, [{"op": "replace", "path": "/a", "value": 99}])
    assert r["a"] == 99
    # Remove
    r = apply_patch(doc, [{"op": "remove", "path": "/a"}])
    assert "a" not in r
    # Array add
    r = apply_patch(doc, [{"op": "add", "path": "/d/-", "value": 4}])
    assert r["d"] == [1, 2, 3, 4]
    # Move
    r = apply_patch(doc, [{"op": "move", "from": "/a", "path": "/x"}])
    assert r["x"] == 1 and "a" not in r
    # Copy
    r = apply_patch(doc, [{"op": "copy", "from": "/a", "path": "/z"}])
    assert r["z"] == 1 and r["a"] == 1
    # Test
    apply_patch(doc, [{"op": "test", "path": "/a", "value": 1}])
    try: apply_patch(doc, [{"op": "test", "path": "/a", "value": 99}]); assert False
    except ValueError: pass
    # Original unchanged
    assert doc["a"] == 1
    print("  json_patch: ALL TESTS PASSED")
