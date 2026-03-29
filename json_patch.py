#!/usr/bin/env python3
"""json_patch - JSON Patch (RFC 6902) operations."""
import sys, json, copy

def apply_patch(doc, patch):
    doc = copy.deepcopy(doc)
    for op in patch:
        if op["op"] == "add":
            _set_path(doc, op["path"], op["value"])
        elif op["op"] == "remove":
            doc = _remove_path(doc, op["path"])
        elif op["op"] == "replace":
            doc = _remove_path(doc, op["path"])
            _set_path(doc, op["path"], op["value"])
        elif op["op"] == "move":
            value = _get_path(doc, op["from"])
            doc = _remove_path(doc, op["from"])
            _set_path(doc, op["path"], value)
        elif op["op"] == "copy":
            value = copy.deepcopy(_get_path(doc, op["from"]))
            _set_path(doc, op["path"], value)
        elif op["op"] == "test":
            actual = _get_path(doc, op["path"])
            if actual != op["value"]:
                raise ValueError(f"Test failed: {actual} != {op['value']}")
    return doc

def _parse_path(path):
    if path == "":
        return []
    parts = path.lstrip("/").split("/")
    return [int(p) if p.isdigit() else p for p in parts]

def _get_path(doc, path):
    parts = _parse_path(path)
    current = doc
    for p in parts:
        current = current[p]
    return current

def _set_path(doc, path, value):
    parts = _parse_path(path)
    if not parts:
        return value
    current = doc
    for p in parts[:-1]:
        current = current[p]
    last = parts[-1]
    if isinstance(current, list) and last == "-":
        current.append(value)
    elif isinstance(current, list):
        current.insert(last, value)
    else:
        current[last] = value
    return doc

def _remove_path(doc, path):
    parts = _parse_path(path)
    if not parts:
        return None
    current = doc
    for p in parts[:-1]:
        current = current[p]
    if isinstance(current, list):
        current.pop(parts[-1])
    else:
        del current[parts[-1]]
    return doc

def diff(a, b, path=""):
    ops = []
    if type(a) != type(b):
        ops.append({"op": "replace", "path": path, "value": b})
    elif isinstance(a, dict):
        for k in set(list(a.keys()) + list(b.keys())):
            p = f"{path}/{k}"
            if k not in a:
                ops.append({"op": "add", "path": p, "value": b[k]})
            elif k not in b:
                ops.append({"op": "remove", "path": p})
            else:
                ops.extend(diff(a[k], b[k], p))
    elif isinstance(a, list):
        if a != b:
            ops.append({"op": "replace", "path": path, "value": b})
    elif a != b:
        ops.append({"op": "replace", "path": path, "value": b})
    return ops

def test():
    doc = {"name": "Alice", "age": 30, "tags": ["a", "b"]}
    patch = [
        {"op": "replace", "path": "/name", "value": "Bob"},
        {"op": "add", "path": "/email", "value": "bob@test.com"},
        {"op": "remove", "path": "/tags/0"},
    ]
    result = apply_patch(doc, patch)
    assert result["name"] == "Bob"
    assert result["email"] == "bob@test.com"
    assert result["tags"] == ["b"]
    # test op
    try:
        apply_patch({"x": 1}, [{"op": "test", "path": "/x", "value": 2}])
        assert False
    except ValueError:
        pass
    # diff
    d = diff({"a": 1, "b": 2}, {"a": 1, "c": 3})
    ops = {o["op"] for o in d}
    assert "remove" in ops and "add" in ops
    print("OK: json_patch")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test()
    else:
        print("Usage: json_patch.py test")
