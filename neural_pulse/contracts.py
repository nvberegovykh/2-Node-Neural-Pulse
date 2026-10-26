"""JSON contracts shared by the editor schemas and runtime validation.

The validator deliberately implements only the schema keywords used here.
It is not a general-purpose JSON Schema implementation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


class ContractError(ValueError):
    pass


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def arr(items, minimum=1, maximum=256):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def number(lo, hi):
    return {"type": "number", "minimum": lo, "maximum": hi}


def integer(lo, hi):
    return {"type": "integer", "minimum": lo, "maximum": hi}


TEXT = {"type": "string", "minLength": 1, "maxLength": 256}
BOOL = {"type": "boolean"}
UNIT = number(-1, 1)
VERSION = {"const": "0.1.0"}

SCHEMAS = {
    "character": obj({
        "schema_version": VERSION, "id": TEXT, "name": TEXT,
        "axes": arr(TEXT, 1, 32), "bias": arr(UNIT, 1, 32),
        "description": TEXT,
    }),
    "emotions": obj({
        "schema_version": VERSION,
        "graphs": arr(obj({
            "id": TEXT,
            "trigger": obj({"sensor": TEXT, "gte": UNIT}),
            "nodes": arr(obj({"id": TEXT, "axis": TEXT, "a": UNIT,
                              "b": integer(0, 255)}), 1, 64),
            "edges": arr(obj({"source": TEXT, "target": TEXT,
                              "weight": UNIT}), 0, 256),
        }), 1, 32),
    }),
    "embodiment": obj({
        "schema_version": VERSION, "id": TEXT,
        "kind": {"enum": ["organic", "synthetic", "cybernetic"]},
        "mode": {"enum": ["simulation", "hardware"]},
        "shape": obj({"description": TEXT, "frame": TEXT,
                      "dimensions_m": arr(number(0.001, 100), 3, 3)}),
        "sensors": arr(obj({"id": TEXT, "unit": {"const": "normalized"}}), 1, 32),
        "manipulators": arr(obj({
            "id": TEXT, "accessible": BOOL, "frame": TEXT,
            "workspace_m": arr(number(0, 100), 3, 3),
            "max_velocity_m_s": number(0, 10),
        }), 1, 32),
    }),
    "controller": obj({
        "schema_version": VERSION,
        "backend": {"enum": ["classical_reference", "qpu_async"]},
        "sensor_weights": arr(arr(number(-2, 2), 1, 32), 1, 32),
        "character_alpha": number(0.05, 1), "emotion_alpha": number(0.05, 1),
        "character_coupling": number(-0.9, 0.9),
        "emotion_coupling": number(-0.9, 0.9),
        "max_iterations": integer(1, 10000), "stable_iterations": integer(1, 100),
        "state_error_tolerance": number(1e-12, 1),
        "deadline_ms": number(0.001, 10000),
        "max_sensor_age_ms": number(0.001, 10000),
        "memory_capacity": integer(1, 10000),
        "compute_j_per_swing": number(0.000001, 1000),
        "reserve_j": number(0, 1e9), "fallback_j": number(0, 1e6),
        "action_j": number(0, 1e6), "max_temperature_c": number(0, 150),
        "max_overload_risk": number(0, 1), "max_uncertainty": number(0, 1),
        "hazard_sensor": TEXT, "hazard_stop_threshold": UNIT,
        "target_manipulator": TEXT,
        "action_weights": arr(UNIT, 1, 32),
        "min_improvement_per_j": number(0, 1e9),
        "stall_iterations": integer(1, 100),
    }),
    "sensor_frame": obj({
        "sequence": integer(0, 2**53 - 1), "timestamp_ms": number(0, 1e16),
        "values": {"type": "object", "additionalProperties": UNIT},
        "uncertainty": number(0, 1),
    }),
    "telemetry": obj({
        "energy_j": number(0, 1e12), "temperature_c": number(-273.15, 1000),
        "overload_risk": number(0, 1), "estop": BOOL,
    }),
}


def validate(value, schema, path="$"):
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ContractError(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: expected one of {schema['enum']}")
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int}
    if kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ContractError(f"{path}: expected finite number")
    elif kind and type(value) is not types[kind]:
        raise ContractError(f"{path}: expected {kind}")
    if kind in ("number", "integer"):
        if not schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf):
            raise ContractError(f"{path}: outside permitted range")
    elif kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", math.inf):
            raise ContractError(f"{path}: invalid text length")
    elif kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", math.inf):
            raise ContractError(f"{path}: invalid array length")
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]")
    elif kind == "object":
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                raise ContractError(f"{path}: missing {key}")
        for key, item in value.items():
            if key in props:
                validate(item, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ContractError(f"{path}: unknown field {key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"], f"{path}.{key}")


def unique(values, name):
    if len(set(values)) != len(values):
        raise ContractError(f"duplicate {name}")


def validate_bundle(bundle):
    if set(bundle) != {"character", "emotions", "embodiment", "controller"}:
        raise ContractError("bundle requires character, emotions, embodiment, controller")
    for name, value in bundle.items():
        validate(value, SCHEMAS[name], name)
    c, e, body, p = (bundle[k] for k in ("character", "emotions", "embodiment", "controller"))
    axes = c["axes"]
    unique(axes, "axis")
    sensors = [s["id"] for s in body["sensors"]]
    unique(sensors, "sensor")
    unique([m["id"] for m in body["manipulators"]], "manipulator")
    unique([g["id"] for g in e["graphs"]], "graph")
    if len(c["bias"]) != len(axes) or len(p["action_weights"]) != len(axes):
        raise ContractError("bias/action_weights must match axes")
    if len(p["sensor_weights"]) != len(axes) or any(len(row) != len(sensors) for row in p["sensor_weights"]):
        raise ContractError("sensor_weights must be axes x sensors")
    if p["stable_iterations"] > p["max_iterations"]:
        raise ContractError("stable_iterations exceeds max_iterations")
    if p["hazard_sensor"] not in sensors:
        raise ContractError("unknown hazard sensor")
    if p["target_manipulator"] not in [m["id"] for m in body["manipulators"]]:
        raise ContractError("unknown target manipulator")
    slots = []
    for graph in e["graphs"]:
        if graph["trigger"]["sensor"] not in sensors:
            raise ContractError("unknown trigger sensor")
        ids = [node["id"] for node in graph["nodes"]]
        unique(ids, "graph node")
        incoming = {key: 0.0 for key in ids}
        for node in graph["nodes"]:
            if node["axis"] not in axes:
                raise ContractError("unknown emotion axis")
            slots.append(node["b"])
        pairs = []
        for edge in graph["edges"]:
            if edge["source"] not in ids or edge["target"] not in ids:
                raise ContractError("dangling graph edge")
            pairs.append((edge["source"], edge["target"]))
            incoming[edge["target"]] += abs(edge["weight"])
        unique(pairs, "graph edge")
        if any(v > 1 + 1e-12 for v in incoming.values()):
            raise ContractError("incoming graph weight absolute sum exceeds 1")
    if sorted(slots) != list(range(len(slots))) or len(slots) > 256:
        raise ContractError("b slots must be globally unique and contiguous from zero; maximum 256")


def load_bundle(directory):
    bundle = {key: json.loads((Path(directory) / f"{key}.json").read_text())
              for key in ("character", "emotions", "embodiment", "controller")}
    validate_bundle(bundle)
    return bundle


def export_schemas(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, schema in SCHEMAS.items():
        value = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                 "title": f"Neural Pulse {name} v0.1.0", **schema}
        (directory / f"{name}.schema.json").write_text(json.dumps(value, indent=2) + "\n")
