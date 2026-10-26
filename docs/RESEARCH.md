# Research grounding

Primary sources reviewed for this formalization on 26 October 2026. Source claims and architectural inferences are kept separate. No source is presented as endorsing Neural Pulse.

## R1. Adaptive recurrent computation

Alex Graves, **Adaptive Computation Time for Recurrent Neural Networks**, 2016; revised 2017. [Paper](https://arxiv.org/abs/1603.08983).

The work learns a variable number of recurrent computation steps between input and output. It supports investigating variable computational effort. Neural Pulse v0.1 uses explicit engineered stopping conditions, not Graves's learned halting mechanism; there is no claim of reproducing its results.

## R2. Deep equilibrium models

Shaojie Bai, J. Zico Kolter, Vladlen Koltun, **Deep Equilibrium Models**, NeurIPS 2019. [Paper](https://arxiv.org/abs/1909.01377).

The authors formulate sequence models through fixed points and root finding, with implicit differentiation. This is a useful connection to repeated refinement and conceptual infinite depth. Neural Pulse instead runs explicit bounded alternating updates with a simple contraction bound; it does not implement DEQ training. Neither formulation supplies infinite physical computation.

## R3. Real-time systems

Jackie Kay / ROS 2 Design, **Introduction to Real-time Systems**, 2016. [Technical design document](https://design.ros2.org/articles/realtime_background.html).

The document distinguishes real-time deadlines from merely low average latency and discusses scheduling, memory allocation, page faults and blocking. This grounds the separation between the Python research prototype and a qualified hardware control path. No hard real-time performance is claimed for this repository.

## R4. QPU execution

IBM Quantum Documentation, **Introduction to IBM Quantum Compute Service execution modes**. [Documentation](https://quantum.cloud.ibm.com/docs/en/guides/execution-modes).

IBM describes job, session and batch execution, including normal queueing for the first job of a session or batch. The proposed architecture therefore places remote quantum work outside immediate actuator deadlines. This is an integration choice inferred from scheduling behavior, not a universal assertion that quantum hardware can never participate in control.

## R5. Boston Dynamics reference

Boston Dynamics, **Boston Dynamics and the Robotics & AI Institute Partner to Advance Humanoid Robots Through Reinforcement Learning**, 5 February 2025. [Company announcement](https://bostondynamics.com/news/boston-dynamics-and-the-robotics-ai-institute-partner/).

The announcement describes a shared reinforcement-learning pipeline for electric Atlas and mobile manipulation. It is relevant context for learned embodied behaviors. It does not document Neural Pulse, a two-pole emotional controller, or a public universal Atlas control interface.

## R6. Tesla Optimus reference

Tesla, **SI & Robotics**. [Company page](https://www.tesla.com/SI).

Tesla describes Optimus as a humanoid project requiring balance, navigation, perception and physical interaction software. These are useful categories for the proposed integration layers. Public descriptions are not an implementation specification or evidence that Optimus uses this two-node architecture. No Optimus SDK integration is implemented or claimed.

## R7. Quantum equilibrium research

Philipp Schleich et al., **Quantum Deep Equilibrium Models**, 2024. [Paper](https://arxiv.org/abs/2410.23940).

The paper explores equilibrium-based training for parameterized quantum circuits in classification experiments. It supplies a directly relevant research lead for the optional quantum branch of this idea. It does not establish robotic control performance, energy efficiency, consciousness, or the feasibility of a compact embodied QPU.

## Evidence map

| Statement | Classification |
|---|---|
| Recurrent models can vary computation between inputs/outputs | Established research direction, R1 |
| Equilibrium formulations connect fixed points and repeated weight sharing | Established formulation, R2 |
| This particular fixed reference map is contractive under its configured bounds | Derivation in ARCHITECTURE.md; executable tests of representative cases |
| Character and emotion graphs improve useful embodied behavior | Hypothesis; requires task benchmarks and ablations |
| Three stable steps imply truth or certainty | Unsupported; not claimed |
| Remote QPU jobs should sit outside this reflex path | Proposed engineering decision informed by R4 |
| Quantum hardware improves Neural Pulse speed or energy | Unmeasured; not claimed |
| Optimus/Atlas use this architecture | Not established by reviewed sources |

The reference is intentionally small enough to falsify assumptions. Next research should compare fixed-step recurrence, resource-bounded recurrence, and a single-pass baseline under matched task, latency, energy and model-capacity budgets.
