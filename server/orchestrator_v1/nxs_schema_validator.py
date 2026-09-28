#!/usr/bin/env python3
"""Orchestrator V1 - validatore JSON Schema minimo, SOLO stdlib (stessa
convenzione gia' stabilita in contracts/validate_registry.py: 'niente
jsonschema, eseguibile ovunque'). Copre il sottoinsieme di draft-07
usato dai 6 schemi di questa fase: type, required, properties, items,
enum, additionalProperties, $ref a #/definitions/, pattern, const."""
import re


def _type_ok(value, expected):
    types = expected if isinstance(expected, list) else [expected]
    for t in types:
        if t == "null" and value is None:
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
    return False


def _resolve(schema, root):
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/definitions/"), f"$ref non supportato: {ref}"
        return root["definitions"][ref.split("/")[-1]]
    return schema


def validate(instance, schema, root=None, path="$"):
    """Ritorna una lista di errori (stringhe) - vuota se valido."""
    root = root or schema
    schema = _resolve(schema, root)
    errors = []

    if "type" in schema and not _type_ok(instance, schema["type"]):
        errors.append(f"{path}: atteso tipo {schema['type']}, trovato {type(instance).__name__}")
        return errors

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: atteso valore costante {schema['const']!r}, trovato {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} non in enum {schema['enum']}")

    if "pattern" in schema and isinstance(instance, str):
        if not re.match(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} non rispetta il pattern {schema['pattern']}")

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: campo richiesto mancante '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props:
                    errors.append(f"{path}: campo non ammesso '{k}' (additionalProperties=False)")
        for k, v in instance.items():
            if k in props:
                errors += validate(v, props[k], root, f"{path}.{k}")

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors += validate(item, schema["items"], root, f"{path}[{i}]")

    return errors


def validate_or_raise(instance, schema, label=""):
    errors = validate(instance, schema)
    if errors:
        raise AssertionError(f"{label}: {len(errors)} errori di validazione:\n" + "\n".join(errors))
    return True
