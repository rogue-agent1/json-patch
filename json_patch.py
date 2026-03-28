#!/usr/bin/env python3
"""json_patch - RFC 6902 JSON Patch implementation."""
import json, sys, copy

def resolve(doc, path):
    if path == "": return doc, None, None
    parts = path.lstrip("/").split("/")
    parts = [p.replace("~1","/").replace("~0","~") for p in parts]
    obj = doc
    for p in parts[:-1]:
        if isinstance(obj, list): obj = obj[int(p)]
        else: obj = obj[p]
    key = parts[-1]
    if isinstance(obj, list): key = int(key) if key != "-" else len(obj)
    return obj, key, parts[-1]

def apply_op(doc, op):
    o = op["op"]
    path = op.get("path","")
    if o == "add":
        parent, key, _ = resolve(doc, path)
        if path == "": return op["value"]
        if isinstance(parent, list): parent.insert(key, op["value"])
        else: parent[key] = op["value"]
    elif o == "remove":
        parent, key, _ = resolve(doc, path)
        if isinstance(parent, list): parent.pop(key)
        else: del parent[key]
    elif o == "replace":
        parent, key, _ = resolve(doc, path)
        if isinstance(parent, list): parent[key] = op["value"]
        else: parent[key] = op["value"]
    elif o == "move":
        src_p, src_k, _ = resolve(doc, op["from"])
        val = src_p[src_k] if isinstance(src_p, dict) else src_p[src_k]
        if isinstance(src_p, list): src_p.pop(src_k)
        else: del src_p[src_k]
        parent, key, _ = resolve(doc, path)
        if isinstance(parent, list): parent.insert(key, val)
        else: parent[key] = val
    elif o == "copy":
        src_p, src_k, _ = resolve(doc, op["from"])
        val = copy.deepcopy(src_p[src_k] if isinstance(src_p, dict) else src_p[src_k])
        parent, key, _ = resolve(doc, path)
        if isinstance(parent, list): parent.insert(key, val)
        else: parent[key] = val
    elif o == "test":
        parent, key, _ = resolve(doc, path)
        actual = parent[key] if isinstance(parent, dict) else parent[key]
        if actual != op["value"]:
            raise ValueError(f"Test failed: {actual} != {op['value']}")
    return doc

def apply_patch(doc, patch):
    for op in patch:
        doc = apply_op(doc, op)
    return doc

def diff(a, b, path=""):
    ops = []
    if type(a) != type(b):
        ops.append({"op":"replace","path":path or "/","value":b})
    elif isinstance(a, dict):
        for k in set(list(a.keys())+list(b.keys())):
            p = f"{path}/{k}"
            if k not in b: ops.append({"op":"remove","path":p})
            elif k not in a: ops.append({"op":"add","path":p,"value":b[k]})
            else: ops.extend(diff(a[k], b[k], p))
    elif isinstance(a, list):
        for i in range(max(len(a),len(b))):
            p = f"{path}/{i}"
            if i >= len(b): ops.append({"op":"remove","path":f"{path}/{len(b)}"})
            elif i >= len(a): ops.append({"op":"add","path":f"{path}/-","value":b[i]})
            else: ops.extend(diff(a[i], b[i], p))
    elif a != b:
        ops.append({"op":"replace","path":path,"value":b})
    return ops

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: json_patch.py <apply|diff> <doc.json> [patch.json|doc2.json]"); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "apply":
        doc = json.load(open(sys.argv[2])); patch = json.load(open(sys.argv[3]))
        print(json.dumps(apply_patch(doc, patch), indent=2))
    elif cmd == "diff":
        a = json.load(open(sys.argv[2])); b = json.load(open(sys.argv[3]))
        print(json.dumps(diff(a, b), indent=2))
