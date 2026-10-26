# Integration boundaries

## What runs today

Only the `classical_reference` backend in `simulation` mode. The example is a scalar virtual manipulator with normalized sensor inputs. It demonstrates the full configuration → sensor → graph → recurrent refinement → gated proposal path.

The default profile represents normal-power operation. Its numerical energy and thermal settings are placeholders. Neither burst/overclock operation nor automatic switching between power modes is implemented.

## Layers for a physical observer–operator

| Layer | Responsibility | v0.1 status |
|---|---|---|
| Device ingress | Timestamp, calibrate, normalize and validate sensor data | Input contract; caller supplies values |
| Perception | Convert raw sensor data into state and calibrated uncertainty | Not implemented |
| Neural Pulse | Character, graphs and bounded iterative proposal | Implemented reference |
| Independent supervisor | Permissions, collision/reachability, watchdog, E-stop, power reserve | Required external component |
| Low-level control | Joint/force/torque control with verified timing | Not implemented |
| Embodiment adapters | Drivers, acknowledgements and measured outcomes | Not implemented |
| Experience store | Approved long-term memories and provenance | Not implemented; temporary memory only |

The supervisor must retain authority even if Neural Pulse blocks, crashes, returns a late result, or emits nonsense. `SAFE_STOP` is a status, not a physical braking command. The appropriate fallback depends on the body: abruptly disabling torque can itself be unsafe for a balancing or load-bearing machine.

## Real-time contract to qualify

For a proposed control period T, budget the complete path:

```math
T_{ingress}+T_{perception}+T_{pulse}+T_{supervision}
+T_{communication}+T_{actuation}+T_{jitter\ margin}\le T.
```

Values require measurement and worst-case analysis on the target processor, operating system, transport and robot. The example's 20 ms pulse deadline is a simulation parameter, not a verified 50 Hz control loop.

The Python reference checks the monotonic clock before and after each swing and immediately before proposal issuance. It cannot preempt a blocking backend or telemetry callback. It allocates Python objects and does not guarantee hard real-time execution. ROS 2's real-time design discussion explains why deadlines, scheduling, memory behavior and nonblocking execution must be considered together [R3](RESEARCH.md#r3-real-time-systems).

Before physical integration:

1. Move deadline-critical code into an appropriate bounded runtime; measure worst-case execution and jitter under load.
2. Preallocate buffers, bound queues, and keep storage/network calls off the control path.
3. Use an independent watchdog and device-specific fallback with a verified deadline.
4. Reject proposals after `valid_until_ms`, on a superseding sensor sequence, or after a configuration version change.
5. Validate geometry, joint, force, velocity and collision constraints against the actual body.
6. Confirm actuator acknowledgement and compare observed motion with prediction. Do not equate sending with successful actuation.
7. Reconcile energy against measured state of charge, discharge rate, temperature, reserve for recovery, and telemetry uncertainty.

The reference `Backend` protocol and telemetry callback are trusted, synchronous testing seams. They must not be used for remote I/O in a hard real-time path. `PulsePort` is single-writer and not thread-safe.

## Embodiment portability

The manifest's shape dimensions and workspace extents are descriptive metadata. They are not URDF, a collision mesh, a kinematic model or a reachability solver. All lengths are metres; virtual speed is metres/second; sensor inputs are dimensionless and normalized before entry.

For a synthetic platform, add a tested robot model and device adapter. For a cybernetic platform, identify which components are biological and which are synthetic, then define interfaces and failure responses explicitly. For an organic target, the category alone grants no ability to interpret, stimulate, or control a nervous system. There are no neural implants, stimulation protocols, or organism experiments in this repository.

## Processor contract

Artist manifests describe behavior independently of processor architecture. An integrator maps them to an approved execution profile. A GPU, NPU or QPU implementation must preserve axis order, graph-slot order, version identity, units and output constraints.

Changing hardware cannot by itself guarantee equivalent behavior: finite precision, approximation, stochastic sampling and latency can all change results. Establish numerical and task-level equivalence for each backend.

## Optional QPU path: asynchronous research interface

`qpu_async` is a reserved configuration identifier and currently raises an explicit error. No cloud account, paid job, circuit, simulator pretending to be a QPU, or hardware assembly is included.

A future design may submit a bounded optimization or inference subproblem outside the reflex path. Proposed job fields:

| Request | Result |
|---|---|
| `job_id`, `manifest_hash`, `sensor_sequence` | Same identity fields |
| `problem_kind`, `payload_hash` | `result_kind`, result payload |
| `submitted_at`, `expires_at` | `completed_at`, expiry status |
| `max_shots`, `max_cost`, provider budget | Actual shots, error estimate, billed usage |
| Approved classical fallback ID | Validation and fallback reason |

Lifecycle: `CREATED → SUBMITTED → PENDING → COMPLETED`, with independent `FAILED`, `CANCELLED` and `EXPIRED` exits. A pending external job is an external wait, not a local control-loop failure. The local classical path continues; late, mismatched or unvalidated results cannot replace its current action.

IBM's execution documentation describes queueing for first jobs in sessions and batches [R4](RESEARCH.md#r4-qpu-execution). **Design inference:** that documented workflow is unsuitable as a dependency for this proposed immediate actuator deadline. A dedicated QPU arrangement would require its own measured end-to-end timing and failure evidence. QPU execution also has finite shots, errors, communication and support-energy costs; no energy saving is assumed.

Quantum Deep Equilibrium Models provide a relevant research connection [R7](RESEARCH.md#r7-quantum-equilibrium-research), but reported classification experiments do not validate this architecture for embodied control. Two classical state vectors are not a quantum state and do not become quantum merely by naming a backend.

## Hardware promotion gates

| Gate | Required evidence |
|---|---|
| Reference correctness | Deterministic replay, input validation, terminal states and budget tests |
| Task usefulness | Benchmarks against single-pass and conventional recurrent baselines; held-out success/error rates |
| Backend qualification | Accuracy, convergence assumptions, execution bounds, energy and failure behavior |
| Simulation embodiment | Physics-based closed-loop tests and adversarial sensor/actuator faults |
| Hardware in the loop | Independent supervision, watchdog and recovery verification |
| Limited physical trial | Device-specific authorization, containment and reproducible evidence |

Only the first gate is partially addressed by the current test suite. Passing it does not authorize later gates automatically.
