#!/usr/bin/env python3
"""json_patch - Apply JSON Patch (RFC 6902) operations."""
import sys, json, copy

def resolve(doc, path):
    parts=path.strip('/').split('/') if path!='/' else []
    node=doc
    for p in parts[:-1]:
        p=int(p) if isinstance(node,list) else p
        node=node[p]
    return node, parts[-1] if parts else None

def apply_op(doc, op):
    doc=copy.deepcopy(doc)
    kind=op['op']; path=op['path']
    if kind=='add':
        parent,key=resolve(doc,path)
        if key is None: return op['value']
        if isinstance(parent,list):
            if key=='-': parent.append(op['value'])
            else: parent.insert(int(key),op['value'])
        else: parent[key]=op['value']
    elif kind=='remove':
        parent,key=resolve(doc,path)
        if isinstance(parent,list): parent.pop(int(key))
        else: del parent[key]
    elif kind=='replace':
        parent,key=resolve(doc,path)
        if isinstance(parent,list): parent[int(key)]=op['value']
        else: parent[key]=op['value']
    elif kind=='move':
        src_parent,src_key=resolve(doc,op['from'])
        val=src_parent[int(src_key) if isinstance(src_parent,list) else src_key]
        if isinstance(src_parent,list): src_parent.pop(int(src_key))
        else: del src_parent[src_key]
        dst_parent,dst_key=resolve(doc,path)
        if isinstance(dst_parent,list): dst_parent.insert(int(dst_key),val)
        else: dst_parent[dst_key]=val
    elif kind=='test':
        parent,key=resolve(doc,path)
        actual=parent[int(key) if isinstance(parent,list) else key]
        assert actual==op['value'], f"Test failed: {actual} != {op['value']}"
    return doc

def apply_patch(doc, patch):
    for op in patch: doc=apply_op(doc,op)
    return doc

def main():
    args=sys.argv[1:]
    if len(args)<2 or '-h' in args:
        print("Usage: json_patch.py DOC.json PATCH.json"); return
    doc=json.loads(open(args[0]).read())
    patch=json.loads(open(args[1]).read())
    result=apply_patch(doc,patch)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
