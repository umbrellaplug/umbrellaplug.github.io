"""Interpret history writes without confusing an unchanged item with a failure."""


def succeeded(result, action='deleted', kind='episodes'):
    if not isinstance(result, dict): return False
    counts = result.get(action)
    if not isinstance(counts, dict) or kind not in counts: return False
    missing = result.get('not_found')
    if isinstance(missing, dict) and any(missing.values()): return False
    if counts[kind]: return True
    return isinstance(missing, dict) and not any(missing.values())
