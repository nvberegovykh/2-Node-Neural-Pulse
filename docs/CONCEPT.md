# Concept and interpretation decisions

Origin: the user's “2 node Neural Pulse” notebook sketch and written description, 26 October 2026. This document distinguishes the supplied idea from implementation choices introduced to make it executable.

## Preserved elements

1. Two poles carrying character and an emotions matrix.
2. A port between them, triggered by sensory input.
3. A character definition that can be authored as a manifest.
4. An emotions matrix represented as a list of graphs, with values `a` and sequence indices `b`.
5. Two parameter vectors repeatedly exchanging updates, with temporary memory.
6. Stopping dependent on required precision, energy availability, reserve, and overload risk.
7. Explicit embodiment configuration: category, shape, physical manipulators and accessibility.
8. A processor abstraction that can describe classical or future quantum computation.

## Formalization choices for v0.1

| Ambiguity | Chosen convention | Why / revision path |
|---|---|---|
| What counts as a node? | A logical computational module | A vector carries many scalar units; two modules do not imply only two neurons |
| Character versus observer | Node C carries character-conditioned observation state | Preserves the Character label; does not claim this is the only possible observer split |
| Emotions versus operator | Node E carries graph-modulated response state | Candidate output is decoded from both nodes |
| Port | Nonlearned coordinator and gatekeeper | Scheduling and limits remain explicit |
| `n` | Length of the graph list | It is computed, not duplicated as a field that could become inconsistent |
| `a` | Signed authored value per graph vertex | Range `[-1,1]`; dimensionless in the reference |
| `b` | Global, zero-based sequence position per vertex | Unique and contiguous across all graphs; editing order does not change slot identity |
| Sensor trigger | Threshold comparison with a normalized input | Graphs can activate simultaneously; inactive slots emit zero |
| Graph operation | One synchronous edge propagation per pulse | Cycles are allowed but do not recursively execute within one evaluation |
| “Swing” | One C update followed by one E update | Uses newly updated C state in the E update |
| Final precision | Numerical fixed-point error tolerance | Separate from task accuracy, sensor uncertainty, or correctness |
| Memory | Last N updates of one pulse, plus last accepted pair for warm start | Bounded retention; no automatic long-term personality rewriting |
| Embodiment kind | `organic`, `synthetic`, `cybernetic` | Categories are metadata, not working biological or mechanical integrations |

The handwritten note near the matrix is not sufficiently clear to treat as a mandatory numeric rule. The example uses three consecutive acceptable iterations as an explicit engineering default; this is not a transcription claim.

## Character and emotion semantics

Here “emotion” means a named computational modulation of attention, response preference, and engagement. Names help artists author and inspect behavior. They do not demonstrate subjective feelings, consciousness, biological emotion, or moral agency. Future mappings can use different axis systems without changing the port contract.

Artist authorship is separated from equipment qualification. A personality may be reused across bodies when the axis contract and sensor mapping are compatible. It cannot itself certify a body, increase its speed limit, grant actuator access, or lower its engineering reserve.

## Proposed architecture, not a novelty claim

Recurrent processing, adaptive computation, graph propagation, and equilibrium methods have established research precedents. Neural Pulse's proposed contribution is their specific two-pole organization and authoring/embodiment contract. This repository does not establish patent novelty, performance superiority, general intelligence, or quantum advantage.
