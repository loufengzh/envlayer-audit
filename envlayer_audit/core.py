"""The audit model never retains configuration values."""
import re

KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
ASSIGNMENT = re.compile(r"(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=(.*)\Z")


def _valid_value(value):
    value = value.strip(" \t")
    if not value or value.startswith("#"):
        return True
    if value[0] in "\"'":
        quote = value[0]
        escaped = False
        for index, char in enumerate(value[1:], 1):
            if escaped:
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                tail = value[index + 1:]
                return not tail or tail.isspace() or (tail[0] in " \t" and tail.lstrip().startswith("#"))
        return False
    # Unquoted quotes and continuation syntax are deliberately unsupported.
    return not any(char in value for char in "\"'") and not value.endswith("\\")


def parse_layer(text, layer):
    """Return occurrences and diagnostics, without retaining RHS strings.

    layer is a caller-assigned integer index. Malformed lines yield generic codes;
    raw lines, malformed keys and values never enter returned data.
    """
    occurrences, diagnostics = [], []
    lines = text.split("\n")
    for number, raw in enumerate(lines, 1):
        # Strip CR only when it belongs to a CRLF pair, never a bare CR.
        if number < len(lines):
            raw = raw.removesuffix("\r")
        line = raw.strip(" \t")
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT.fullmatch(line)
        if not match or any((ord(char) < 32 and char != "\t") or ord(char) == 127 for char in line):
            diagnostics.append({"code": "invalid_assignment", "layer": layer, "line": number})
        elif not _valid_value(match[2]):
            diagnostics.append({"code": "unsupported_value_syntax", "layer": layer, "line": number})
        else:
            occurrences.append({"key": match[1], "layer": layer, "line": number})
    return occurrences, diagnostics


def validate_policy(policy):
    """Validate exact-key JSON policy; raise only value-free ValueError messages."""
    if not isinstance(policy, dict) or set(policy) - {"required", "allowed", "protected"}:
        raise ValueError("invalid_policy")
    for value in policy.values():
        if not isinstance(value, list) or any(not isinstance(key, str) or not KEY.fullmatch(key) for key in value):
            raise ValueError("invalid_policy")
        if len(set(value)) != len(value):
            raise ValueError("invalid_policy")
    if "allowed" in policy and not set(policy.get("required", [])) <= set(policy["allowed"]):
        raise ValueError("inconsistent_policy")
    return policy


def audit(layers, policy=None):
    """Audit an iterable of layer texts in ascending precedence.

    Last valid occurrence wins. Any parse error makes the report incomplete and
    skips all policy evaluation, preventing a partial map from appearing valid.
    """
    policy = validate_policy({} if policy is None else policy)
    history, diagnostics, count = {}, [], 0
    for count, text in enumerate(layers, 1):
        occurrences, errors = parse_layer(text, count)
        diagnostics.extend(errors)
        for occurrence in occurrences:
            history.setdefault(occurrence["key"], []).append(occurrence)
    keys = []
    for key, occurrences in sorted(history.items()):
        keys.append({"key": key, "winner": occurrences[-1], "history": occurrences,
                     "overrides": len(occurrences) - 1})
    complete = not diagnostics
    if complete:
        for key in sorted(set(policy.get("required", [])) - history.keys()):
            diagnostics.append({"code": "missing_required", "key": key})
        for key, occurrences in sorted(history.items()):
            if "allowed" in policy and key not in policy["allowed"]:
                diagnostics.append({"code": "not_allowed", "key": key})
            if key in policy.get("protected", []) and len(occurrences) > 1:
                diagnostics.append({"code": "protected_redefined", "key": key,
                                    "locations": occurrences})
    return {"schema_version": 1, "complete": complete, "ok": not diagnostics,
            "layer_count": count, "keys": keys, "diagnostics": diagnostics}
