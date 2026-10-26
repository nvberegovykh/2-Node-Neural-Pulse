"""Two recurrent poles and a bounded central port, for simulation only."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import time
from typing import Callable, Protocol

from .contracts import ContractError, SCHEMAS, validate, validate_bundle


Vector = tuple[float, ...]


def clip(x, low=-1.0, high=1.0):
    return max(low, min(high, x))


@dataclass(frozen=True)
class Frame:
    sequence: int
    timestamp_ms: float
    values: dict[str, float]
    uncertainty: float


@dataclass(frozen=True)
class Telemetry:
    energy_j: float
    temperature_c: float
    overload_risk: float
    estop: bool = False


@dataclass(frozen=True)
class Outcome:
    status: str
    reason: str
    iterations: int
    residual: float | None
    state_error_bound: float | None
    compute_j: float
    committed_j: float
    remaining_j: float
    elapsed_ms: float
    sequence: int
    manifest_sha256: str
    character_state: Vector
    emotion_state: Vector
    output_sequence: tuple[dict, ...]
    proposal: dict | None
    trace: tuple[dict, ...]


class Backend(Protocol):
    """Trusted bounded compute. No device I/O; see docs/INTEGRATION.md."""
    def step(self, u: Vector, v: Vector, drive: Vector, modulation: Vector,
             controller: dict) -> tuple[Vector, Vector]: ...


class ClassicalReference:
    def step(self, u, v, drive, modulation, controller):
        a, b = controller["character_alpha"], controller["emotion_alpha"]
        r, s = controller["character_coupling"], controller["emotion_coupling"]
        un = tuple((1-a)*x + a*math.tanh(d + r*y) for x, y, d in zip(u, v, drive))
        vn = tuple((1-b)*y + b*math.tanh(m + s*x) for x, y, m in zip(un, v, modulation))
        return un, vn


def emotion_output(emotions, axes, values):
    """One synchronous graph propagation, then stable b-order serialization."""
    result = []
    sums = {axis: 0.0 for axis in axes}
    for graph in emotions["graphs"]:
        trigger = graph["trigger"]
        active = values[trigger["sensor"]] >= trigger["gte"]
        base = {node["id"]: node["a"] if active else 0.0 for node in graph["nodes"]}
        propagated = dict(base)
        for edge in graph["edges"]:
            propagated[edge["target"]] += edge["weight"] * base[edge["source"]]
        for node in graph["nodes"]:
            value = clip(propagated[node["id"]])
            sums[node["axis"]] += value
            result.append({"graph": graph["id"], "node": node["id"], "b": node["b"],
                           "axis": node["axis"], "a": node["a"], "value": value,
                           "active": active})
    return tuple(sorted(result, key=lambda item: item["b"])), tuple(clip(sums[a]) for a in axes)


class PulsePort:
    """Single-writer, one request at a time; configuration frozen at construction.

    Energy is an illustrative ledger, not a battery measurement. Reconcile it
    conservatively against new telemetry on each request. Never auto-recharge.
    """
    def __init__(self, bundle, *, clock_ms: Callable[[], float] | None = None,
                 backend: Backend | None = None):
        validate_bundle(bundle)
        self._bundle = deepcopy(bundle)
        self._p = self._bundle["controller"]
        body = self._bundle["embodiment"]
        if body["mode"] != "simulation":
            raise ContractError("hardware mode is not implemented")
        if self._p["backend"] != "classical_reference":
            raise ContractError("qpu_async is a reserved interface, not an implemented backend")
        self._clock = clock_ms or (lambda: time.monotonic_ns()/1e6)
        self._backend = backend or ClassicalReference()
        self._last_sequence = -1
        self._last_timestamp = -1.0
        self._remaining = None
        self._u = (0.0,) * len(self._bundle["character"]["axes"])
        self._v = self._u
        self._memory = deque(maxlen=self._p["memory_capacity"])
        self._hash = hashlib.sha256(json.dumps(self._bundle, sort_keys=True,
                                              separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def pulse(self, frame: Frame, telemetry: Telemetry, *,
              read_telemetry: Callable[[], Telemetry] | None = None) -> Outcome:
        p, bundle = self._p, self._bundle
        start = self._clock()
        if not math.isfinite(start):
            raise ContractError("clock must be finite and monotonic")
        previous_clock = start
        # Reject malformed inputs before they can change persistent state.
        validate(asdict(frame), SCHEMAS["sensor_frame"], "frame")
        validate(asdict(telemetry), SCHEMAS["telemetry"], "telemetry")
        expected = [s["id"] for s in bundle["embodiment"]["sensors"]]
        if set(frame.values) != set(expected):
            raise ContractError("frame must contain exactly the declared sensors")
        values = dict(frame.values)  # one immutable-in-practice snapshot per pulse
        u, v = self._u, self._v
        self._memory.clear()  # temporary memory never grows across requests
        iterations, stable, stalls = 0, 0, 0
        residual = error_bound = last_error = None
        spent = committed = 0.0
        outputs = ()
        initial = telemetry.energy_j if self._remaining is None else min(self._remaining, telemetry.energy_j)
        remaining = initial
        a, b = p["character_alpha"], p["emotion_alpha"]
        qc = 1-a+a*abs(p["character_coupling"])
        q = max(qc, 1-b+b*abs(p["emotion_coupling"])*qc)

        def now_ms():
            nonlocal previous_clock
            now = self._clock()
            if not math.isfinite(now) or now < previous_clock:
                raise ContractError("clock must be finite and monotonic")
            previous_clock = now
            return now

        def finish(status, reason, proposal=None):
            nonlocal committed, remaining
            # Commit action allocation or fallback allocation exactly once.
            committed = p["action_j"] if proposal is not None else min(p["fallback_j"], remaining)
            remaining = max(0.0, remaining-committed)
            self._remaining = remaining
            # Failed refinement cannot poison the next request's warm start.
            if status == "CONVERGED":
                self._u, self._v = u, v
            return Outcome(status, reason, iterations, residual, error_bound, spent,
                           committed, remaining, max(0, previous_clock-start), frame.sequence,
                           self._hash, u, v, outputs, proposal, tuple(deepcopy(self._memory)))

        def gate():
            nonlocal remaining
            try:
                current = read_telemetry() if read_telemetry else telemetry
                validate(asdict(current), SCHEMAS["telemetry"], "telemetry")
                now = now_ms()
            except Exception:
                return "FAULT", "telemetry_or_clock_failure"
            remaining = min(remaining, current.energy_j)
            if current.estop:
                return "SAFE_STOP", "emergency_stop"
            if current.temperature_c >= p["max_temperature_c"]:
                return "SAFE_STOP", "thermal_limit"
            if current.overload_risk >= p["max_overload_risk"]:
                return "SAFE_STOP", "overload_limit"
            age = now-frame.timestamp_ms
            if age < 0:
                return "REJECTED", "future_sensor_frame"
            if age > p["max_sensor_age_ms"]:
                return "REJECTED", "stale_sensor_frame"
            if now-start >= p["deadline_ms"]:
                return "DEFERRED", "deadline"
            if values[p["hazard_sensor"]] >= p["hazard_stop_threshold"]:
                return "SAFE_STOP", "hazard_limit"
            if frame.uncertainty > p["max_uncertainty"]:
                return "DEFERRED", "sensor_uncertainty"
            if remaining < p["reserve_j"]+p["fallback_j"]:
                return "SAFE_STOP", "reserve_unavailable"
            return None

        if frame.sequence <= self._last_sequence or frame.timestamp_ms < self._last_timestamp:
            return finish("REJECTED", "out_of_order_sensor_frame")
        blocked = gate()
        if blocked:
            return finish(*blocked)
        self._last_sequence, self._last_timestamp = frame.sequence, frame.timestamp_ms
        target = next(m for m in bundle["embodiment"]["manipulators"]
                      if m["id"] == p["target_manipulator"])
        if not target["accessible"]:
            return finish("REJECTED", "manipulator_inaccessible")
        outputs, modulation = emotion_output(bundle["emotions"], bundle["character"]["axes"], values)
        sensors = [values[sensor] for sensor in expected]
        drive = tuple(c+sum(w*x for w, x in zip(row, sensors))
                      for c, row in zip(bundle["character"]["bias"], p["sensor_weights"]))
        for _ in range(p["max_iterations"]):
            blocked = gate()
            if blocked:
                return finish(*blocked)
            required = p["reserve_j"]+p["fallback_j"]+p["action_j"]+p["compute_j_per_swing"]
            if remaining < required:
                return finish("DEFERRED", "energy_budget")
            remaining -= p["compute_j_per_swing"]
            spent += p["compute_j_per_swing"]
            iterations += 1
            try:
                un, vn = self._backend.step(u, v, drive, modulation, deepcopy(p))
                if len(un) != len(u) or len(vn) != len(v):
                    raise ValueError("backend shape mismatch")
                if any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1
                       for x in (*un, *vn)):
                    raise ValueError("nonfinite or unbounded backend output")
                un, vn = tuple(un), tuple(vn)
            except Exception:
                return finish("FAULT", "backend_failure")
            residual = max(abs(x-y) for x, y in zip((*un, *vn), (*u, *v)))
            error_bound = q/(1-q)*residual if type(self._backend) is ClassicalReference else None
            u, v = un, vn
            self._memory.append({"iteration": iterations, "character": u, "emotion": v,
                                 "residual": residual, "state_error_bound": error_bound,
                                 "remaining_j": remaining})
            # Check after compute and again before issuing the proposal.
            blocked = gate()
            if blocked:
                return finish(*blocked)
            metric = error_bound if error_bound is not None else residual
            stable = stable+1 if metric <= p["state_error_tolerance"] else 0
            if stable >= p["stable_iterations"]:
                # Fixed-point bound is valid only for the built-in reference map.
                if type(self._backend) is not ClassicalReference:
                    return finish("DEFERRED", "unverified_backend")
                speed = target["max_velocity_m_s"]*clip(
                    0.5+sum(w*(x+y)/2 for w, x, y in zip(p["action_weights"], u, v)), 0, 1)
                blocked = gate()
                if blocked:
                    return finish(*blocked)
                if remaining < p["reserve_j"]+p["fallback_j"]+p["action_j"]:
                    return finish("DEFERRED", "energy_budget")
                proposal = {"kind": "simulated_velocity", "manipulator": target["id"],
                            "frame": target["frame"], "velocity_m_s": speed,
                            "source_sequence": frame.sequence,
                            "valid_until_ms": min(start+p["deadline_ms"],
                                                  frame.timestamp_ms+p["max_sensor_age_ms"])}
                return finish("CONVERGED", "state_tolerance_met", proposal)
            if last_error is not None and metric > p["state_error_tolerance"]:
                gain = (last_error-metric)/p["compute_j_per_swing"]
                stalls = stalls+1 if gain <= p["min_improvement_per_j"] else 0
                if stalls >= p["stall_iterations"]:
                    return finish("DEFERRED", "insufficient_improvement_per_joule")
            last_error = metric
        return finish("DEFERRED", "iteration_limit")
