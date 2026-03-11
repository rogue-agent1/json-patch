#!/usr/bin/env python3
"""json_patch.py — RFC 6902 JSON Patch implementation.

Apply, generate, and validate JSON Patch operations: add, remove,
replace, move, copy, test. Includes JSON Pointer (RFC 6901) resolution
and diff generation between two JSON documents.

One file. Zero deps. Does one thing well.
"""

import copy
import json
import sys


class JsonPatchError(Exception):
    pass


def resolve_pointer(doc, pointer: str):
    """RFC 6901 JSON Pointer resolution. Returns (parent, key, value)."""
    if pointer == '':
        return None, None, doc
    parts = pointer.lstrip('/').split('/')
    parts = [p.replace('~1', '/').replace('~0', '~') for p in parts]
    current = doc
    for i, part in enumerate(parts[:-1]):
        if isinstance(current, list):
            idx = int(part) if part != '-' else len(current)
            current = current[idx]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise JsonPatchError(f"Cannot traverse {type(current)} at /{'/'.join(parts[:i+1])}")
    last = parts[-1]
    if isinstance(current, list):
        idx = len(current) if last == '-' else int(last)
        val = current[idx] if idx < len(current) else None
        return current, idx, val
    elif isinstance(current, dict):
        return current, last, current.get(last)
    raise JsonPatchError(f"Cannot resolve pointer: {pointer}")


def _set_value(parent, key, value):
    if isinstance(parent, list):
        if key >= len(parent):
            parent.append(value)
        else:
            parent.insert(key, value)
    elif isinstance(parent, dict):
        parent[key] = value


def _remove_value(parent, key):
    if isinstance(parent, list):
        del parent[key]
    elif isinstance(parent, dict):
        del parent[key]


def apply_patch(doc, patch: list[dict]):
    """Apply a JSON Patch (list of operations) to a document."""
    doc = copy.deepcopy(doc)
    for op in patch:
        operation = op.get('op')
        path = op.get('path', '')

        if operation == 'add':
            if path == '':
                doc = op['value']
                continue
            parent, key, _ = resolve_pointer(doc, path)
            _set_value(parent, key, copy.deepcopy(op['value']))

        elif operation == 'remove':
            parent, key, _ = resolve_pointer(doc, path)
            if parent is None:
                raise JsonPatchError("Cannot remove root")
            _remove_value(parent, key)

        elif operation == 'replace':
            if path == '':
                doc = op['value']
                continue
            parent, key, _ = resolve_pointer(doc, path)
            if isinstance(parent, list):
                parent[key] = copy.deepcopy(op['value'])
            else:
                parent[key] = copy.deepcopy(op['value'])

        elif operation == 'move':
            from_parent, from_key, value = resolve_pointer(doc, op['from'])
            _remove_value(from_parent, from_key)
            if path == '':
                doc = value
                continue
            parent, key, _ = resolve_pointer(doc, path)
            _set_value(parent, key, value)

        elif operation == 'copy':
            _, _, value = resolve_pointer(doc, op['from'])
            if path == '':
                doc = copy.deepcopy(value)
                continue
            parent, key, _ = resolve_pointer(doc, path)
            _set_value(parent, key, copy.deepcopy(value))

        elif operation == 'test':
            _, _, value = resolve_pointer(doc, path)
            if value != op['value']:
                raise JsonPatchError(f"Test failed: {path} is {value!r}, expected {op['value']!r}")

        else:
            raise JsonPatchError(f"Unknown operation: {operation}")

    return doc


def diff(a, b, path: str = '') -> list[dict]:
    """Generate JSON Patch from a to b."""
    if a == b:
        return []
    if type(a) != type(b) or not isinstance(a, (dict, list)):
        return [{'op': 'replace', 'path': path or '/', 'value': b}]

    ops = []
    if isinstance(a, dict):
        for key in set(list(a.keys()) + list(b.keys())):
            p = f"{path}/{key.replace('~', '~0').replace('/', '~1')}"
            if key not in b:
                ops.append({'op': 'remove', 'path': p})
            elif key not in a:
                ops.append({'op': 'add', 'path': p, 'value': b[key]})
            else:
                ops.extend(diff(a[key], b[key], p))
    elif isinstance(a, list):
        # Simple diff: replace differing elements, add/remove tail
        for i in range(min(len(a), len(b))):
            ops.extend(diff(a[i], b[i], f"{path}/{i}"))
        if len(a) > len(b):
            for i in range(len(a) - 1, len(b) - 1, -1):
                ops.append({'op': 'remove', 'path': f"{path}/{i}"})
        elif len(b) > len(a):
            for i in range(len(a), len(b)):
                ops.append({'op': 'add', 'path': f"{path}/-", 'value': b[i]})

    return ops


def demo():
    print("=== JSON Patch (RFC 6902) ===\n")
    doc = {"name": "Rogue", "version": 1, "tags": ["ai", "agent"], "config": {"debug": False}}
    print(f"Original: {json.dumps(doc)}\n")

    patch = [
        {"op": "replace", "path": "/version", "value": 2},
        {"op": "add", "path": "/tags/-", "value": "autonomous"},
        {"op": "remove", "path": "/config/debug"},
        {"op": "add", "path": "/config/verbose", "value": True},
        {"op": "copy", "from": "/name", "path": "/config/owner"},
        {"op": "test", "path": "/name", "value": "Rogue"},
    ]
    print("Patch:")
    for op in patch:
        print(f"  {json.dumps(op)}")

    result = apply_patch(doc, patch)
    print(f"\nResult: {json.dumps(result, indent=2)}")

    # Diff
    print("\nGenerated diff (original → result):")
    generated = diff(doc, result)
    for op in generated:
        print(f"  {json.dumps(op)}")

    # Verify round-trip
    reconstructed = apply_patch(doc, generated)
    print(f"\nRound-trip match: {reconstructed == result}")


if __name__ == '__main__':
    if '--test' in sys.argv:
        # Add
        assert apply_patch({"a": 1}, [{"op": "add", "path": "/b", "value": 2}]) == {"a": 1, "b": 2}
        # Remove
        assert apply_patch({"a": 1, "b": 2}, [{"op": "remove", "path": "/b"}]) == {"a": 1}
        # Replace
        assert apply_patch({"a": 1}, [{"op": "replace", "path": "/a", "value": 99}]) == {"a": 99}
        # Move
        assert apply_patch({"a": 1, "b": 2}, [{"op": "move", "from": "/a", "path": "/c"}]) == {"b": 2, "c": 1}
        # Copy
        assert apply_patch({"a": 1}, [{"op": "copy", "from": "/a", "path": "/b"}]) == {"a": 1, "b": 1}
        # Test pass
        apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 1}])
        # Test fail
        try:
            apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])
            assert False
        except JsonPatchError: pass
        # Array ops
        assert apply_patch([1,2,3], [{"op": "add", "path": "/1", "value": 99}]) == [1, 99, 2, 3]
        assert apply_patch([1,2,3], [{"op": "remove", "path": "/1"}]) == [1, 3]
        # Diff
        d = diff({"a": 1}, {"a": 2, "b": 3})
        r = apply_patch({"a": 1}, d)
        assert r == {"a": 2, "b": 3}
        print("All tests passed ✓")
    else:
        demo()
