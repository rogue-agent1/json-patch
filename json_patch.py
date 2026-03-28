#!/usr/bin/env python3
"""JSON Patch (RFC 6902) from scratch."""
import sys,json,copy

def resolve(doc, path):
    if path == "": return doc, None, None
    parts = path.lstrip("/").split("/")
    obj = doc
    for p in parts[:-1]:
        p = p.replace("~1","/").replace("~0","~")
        obj = obj[int(p)] if isinstance(obj,list) else obj[p]
    key = parts[-1].replace("~1","/").replace("~0","~")
    return obj, key, int(key) if isinstance(obj,list) else key

def apply_patch(doc, patch):
    doc = copy.deepcopy(doc)
    for op in patch:
        o = op["op"]; path = op["path"]
        if o == "add":
            parent, key, _ = resolve(doc, path)
            if isinstance(parent, list):
                if key == "-": parent.append(op["value"])
                else: parent.insert(int(key), op["value"])
            else: parent[key] = op["value"]
        elif o == "remove":
            parent, key, idx = resolve(doc, path)
            if isinstance(parent, list): parent.pop(idx)
            else: del parent[key]
        elif o == "replace":
            parent, key, idx = resolve(doc, path)
            if isinstance(parent, list): parent[idx] = op["value"]
            else: parent[key] = op["value"]
        elif o == "test":
            parent, key, idx = resolve(doc, path)
            val = parent[idx] if isinstance(parent, list) else parent[key]
            if val != op["value"]: raise ValueError(f"Test failed: {val}!={op['value']}")
    return doc

def main():
    if "--demo" in sys.argv:
        doc = {"name":"Alice","age":30,"tags":["admin"]}
        patch = [
            {"op":"replace","path":"/name","value":"Bob"},
            {"op":"add","path":"/email","value":"bob@x.com"},
            {"op":"add","path":"/tags/-","value":"user"},
            {"op":"remove","path":"/age"},
        ]
        result = apply_patch(doc, patch)
        print(f"Before: {json.dumps(doc)}")
        print(f"After:  {json.dumps(result)}")
    else:
        d = json.loads(sys.stdin.read())
        print(json.dumps(apply_patch(d["doc"], d["patch"]), indent=2))
if __name__=="__main__": main()
