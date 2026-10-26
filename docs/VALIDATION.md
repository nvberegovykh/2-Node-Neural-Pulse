# Validation and implementation gates

## Executed checks

Validated on Python 3.12.14 in the development environment, 26 October 2026:

```bash
python -m neural_pulse schemas
python -m neural_pulse validate
python -m neural_pulse demo --output examples/normal-result.json
python -m unittest discover -s tests -v
```

The initial suite contains **32 passing tests**. Tests use a virtual monotonic clock; they verify logical scheduling checks, not operating-system scheduling guarantees.

| Area | Evidence |
|---|---|
| Numerics | Reference convergence; coarse error bound compared with a tighter solution |
| Graph semantics | Sensor activation, edge propagation, simultaneous graphs and `b` ordering |
| Reproducibility | Identical replay and checked-in example hash/output |
| Budgets | Iteration cap, bounded memory, action/compute/fallback accounting, reserve boundary, empty battery, no implicit recharge |
| Observation freshness | Stale/future/reordered samples and expiry during computation |
| Interrupts | E-stop during a swing; thermal/overload/hazard/uncertainty gates |
| Final acceptance | Deadline after compute and energy drop immediately before proposal |
| Backend failure | Exceptions, malformed/nonfinite outputs, slow backend, oscillation and unverified backend |
| Configuration | Cross-file checks, prohibited artist fields, immutable configuration copy, unsupported hardware/QPU modes |
| Schemas | Exported JSON schemas match the runtime contract definitions |

The checked-in JSON trace is a simulation output with illustrative energy. No physical current, temperature, force, latency or task-success measurement has been taken.

## Known limitations

- Fixed authored weights; no training, sensory perception, learned uncertainty or task model.
- Synchronous single-writer processing; no request queue, preemption or asynchronous supersession.
- Temporary trace eviction is intentional; full trace export requires an external bounded sink.
- The state-error bound assumes the fixed reference map and exact arithmetic; it is not a proof for arbitrary backends or floating-point error at arbitrarily small tolerances.
- Budget constants exclude initialization, graph evaluation and callback costs; they require calibration before any hardware use.
- A fallback debit is a bookkeeping allocation. No physical fallback is executed.
- Every terminal pulse allocates fallback unless it issues a proposal, including rejected inputs. A deployment ingress should rate-limit invalid traffic and handle duplicate messages before this simulation ledger.
- Geometry fields are metadata; only accessibility and scalar speed bounds affect the current output.
- JSON validation and hashes do not implement authentication, isolation, or access control.
- `qpu_async` and hardware mode deliberately fail on construction instead of silently pretending to work.

## Next work, in dependency order

1. Select a concrete simulated task and body; define observable success, failure and precision requirements.
2. Add a physics/sensor adapter, calibrated uncertainty, superseding observations and command acknowledgement.
3. Benchmark against single-pass and conventional recurrent baselines with matched compute and energy accounting.
4. Add a learned C/E model if the task benefits; establish its stability or retain hard terminal limits without claiming convergence.
5. Qualify an independent supervisor and bounded execution backend before hardware-in-the-loop work.
6. Evaluate a QPU subproblem only if a measurable advantage is plausible; include queueing, shots, error mitigation and total support energy in the comparison.

## Preservation and rollback

The initial repository commit and MIT license are preserved. The formalization is a new descendant commit with no history rewrite. To undo it, revert that commit through normal Git history. No deployed service, device configuration, paid compute job or credential was changed by this work.
