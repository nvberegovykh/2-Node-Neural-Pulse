from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from neural_pulse.contracts import ContractError, SCHEMAS, export_schemas, load_bundle, validate_bundle
from neural_pulse.engine import ClassicalReference, Frame, PulsePort, Telemetry, emotion_output

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self, step=0.01):
        self.now, self.step = 1000.0, step

    def __call__(self):
        value = self.now
        self.now += self.step
        return value


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_bundle(ROOT / "examples")
        self.frame = Frame(1, 1000, {"hazard": 0.1, "novelty": 0.8, "contact": 0.2}, 0.1)
        self.telemetry = Telemetry(100, 35, 0.05)

    def run_pulse(self, **kwargs):
        return PulsePort(self.bundle, clock_ms=Clock(), **kwargs).pulse(self.frame, self.telemetry)

    def test_converges_with_bounded_proposal_and_energy_ledger(self):
        result = self.run_pulse()
        self.assertEqual(result.status, "CONVERGED")
        self.assertLessEqual(result.state_error_bound, 0.001)
        self.assertLessEqual(result.proposal["velocity_m_s"], 0.05)
        self.assertGreaterEqual(result.proposal["velocity_m_s"], 0)
        self.assertAlmostEqual(result.compute_j, result.iterations*0.02)
        self.assertAlmostEqual(result.remaining_j+result.compute_j+result.committed_j, 100)
        self.assertGreaterEqual(result.remaining_j, 11)

    def test_reference_error_bound_contains_high_precision_solution(self):
        coarse = self.run_pulse()
        self.bundle["controller"]["state_error_tolerance"] = 1e-12
        precise = self.run_pulse()
        self.assertEqual(precise.status, "CONVERGED")
        difference = max(abs(x-y) for x, y in zip(
            coarse.character_state+coarse.emotion_state,
            precise.character_state+precise.emotion_state))
        self.assertLessEqual(difference, coarse.state_error_bound+1e-11)

    def test_graph_trigger_propagation_and_order(self):
        result = self.run_pulse()
        outputs = result.output_sequence
        self.assertEqual([o["b"] for o in outputs], [0, 1, 2, 3])
        self.assertAlmostEqual(outputs[1]["value"], 0.34)
        self.assertFalse(outputs[2]["active"])
        self.assertEqual(outputs[2]["value"], 0)

    def test_multiple_active_graphs(self):
        values = {"hazard": 0.5, "novelty": 0.8, "contact": 0.2}
        outputs, modulation = emotion_output(self.bundle["emotions"], self.bundle["character"]["axes"], values)
        self.assertTrue(all(item["active"] for item in outputs))
        self.assertAlmostEqual(modulation[2], -0.32)

    def test_deterministic_replay(self):
        self.assertEqual(asdict(self.run_pulse()), asdict(self.run_pulse()))

    def test_temporary_memory_is_bounded(self):
        self.bundle["controller"]["memory_capacity"] = 3
        result = self.run_pulse()
        self.assertEqual(len(result.trace), 3)
        self.assertGreater(result.trace[0]["iteration"], 1)

    def test_iteration_limit_never_issues_action(self):
        self.bundle["controller"].update(max_iterations=1, stable_iterations=1, state_error_tolerance=1e-12)
        result = self.run_pulse()
        self.assertEqual(result.reason, "iteration_limit")
        self.assertIsNone(result.proposal)

    def test_stale_sensor(self):
        self.frame = Frame(1, 900, self.frame.values, 0.1)
        self.assertEqual(self.run_pulse().reason, "stale_sensor_frame")

    def test_future_frame_does_not_poison_valid_sequence(self):
        port = PulsePort(self.bundle, clock_ms=Clock())
        future = Frame(999, 2000, self.frame.values, 0.1)
        self.assertEqual(port.pulse(future, self.telemetry).reason, "future_sensor_frame")
        self.assertEqual(port.pulse(self.frame, self.telemetry).status, "CONVERGED")

    def test_sensor_expires_during_refinement(self):
        self.bundle["controller"]["max_sensor_age_ms"] = 0.025
        result = self.run_pulse()
        self.assertEqual(result.reason, "stale_sensor_frame")
        self.assertIsNone(result.proposal)

    def test_reordered_sequence_and_timestamp_rejected(self):
        port = PulsePort(self.bundle, clock_ms=Clock())
        self.assertEqual(port.pulse(self.frame, self.telemetry).status, "CONVERGED")
        self.assertEqual(port.pulse(self.frame, self.telemetry).reason, "out_of_order_sensor_frame")
        older = Frame(2, 999, self.frame.values, 0.1)
        self.assertEqual(port.pulse(older, self.telemetry).reason, "out_of_order_sensor_frame")

    def test_deadline_and_no_post_deadline_proposal(self):
        self.bundle["controller"]["deadline_ms"] = 0.025
        result = self.run_pulse()
        self.assertEqual(result.reason, "deadline")
        self.assertEqual(result.iterations, 1)
        self.assertIsNone(result.proposal)

    def test_low_energy_retains_reserve(self):
        self.telemetry = Telemetry(11, 35, 0.05)
        result = self.run_pulse()
        self.assertEqual(result.reason, "energy_budget")
        self.assertEqual(result.iterations, 0)
        self.assertEqual(result.remaining_j, 10)

    def test_unavailable_reserve_and_empty_battery(self):
        for energy in [0, 1, 10.5]:
            with self.subTest(energy=energy):
                self.telemetry = Telemetry(energy, 35, 0.05)
                result = self.run_pulse()
                self.assertEqual(result.reason, "reserve_unavailable")
                self.assertGreaterEqual(result.remaining_j, 0)
                self.assertIsNone(result.proposal)

    def test_no_automatic_recharge_between_requests(self):
        port = PulsePort(self.bundle, clock_ms=Clock())
        first = port.pulse(self.frame, self.telemetry)
        second = port.pulse(Frame(2, 1000, self.frame.values, 0.1), Telemetry(1000, 35, 0.05))
        self.assertLess(second.remaining_j, first.remaining_j)

    def test_safety_telemetry_limits(self):
        cases = [(Telemetry(100, 80, 0.05), "thermal_limit"),
                 (Telemetry(100, 35, 0.4), "overload_limit"),
                 (Telemetry(100, 35, 0.05, True), "emergency_stop")]
        for telemetry, reason in cases:
            with self.subTest(reason=reason):
                self.telemetry = telemetry
                result = self.run_pulse()
                self.assertEqual(result.reason, reason)
                self.assertIsNone(result.proposal)

    def test_hazard_and_uncertainty(self):
        self.frame = Frame(1, 1000, {**self.frame.values, "hazard": 0.9}, 0.1)
        self.assertEqual(self.run_pulse().reason, "hazard_limit")
        self.frame = Frame(1, 1000, {**self.frame.values, "hazard": 0.1}, 0.9)
        self.assertEqual(self.run_pulse().reason, "sensor_uncertainty")

    def test_emergency_stop_arrives_mid_swing(self):
        calls = [0]
        def telemetry():
            calls[0] += 1
            return Telemetry(100, 35, 0.05, calls[0] >= 3)
        result = PulsePort(self.bundle, clock_ms=Clock()).pulse(
            self.frame, self.telemetry, read_telemetry=telemetry)
        self.assertEqual(result.reason, "emergency_stop")
        self.assertEqual(result.iterations, 1)
        self.assertIsNone(result.proposal)

    def test_final_energy_recheck_blocks_proposal(self):
        n = self.run_pulse().iterations
        calls = [0]
        def telemetry():
            calls[0] += 1
            return Telemetry(11 if calls[0] >= 2*n+2 else 100, 35, 0.05)
        result = PulsePort(self.bundle, clock_ms=Clock()).pulse(
            self.frame, self.telemetry, read_telemetry=telemetry)
        self.assertEqual(result.reason, "energy_budget")
        self.assertIsNone(result.proposal)

    def test_inaccessible_manipulator(self):
        self.bundle["embodiment"]["manipulators"][0]["accessible"] = False
        self.assertEqual(self.run_pulse().reason, "manipulator_inaccessible")

    def test_backend_nonfinite_shape_and_exception(self):
        class Broken:
            def __init__(self, mode): self.mode = mode
            def step(self, u, v, *args):
                if self.mode == "nan": return (float("nan"),)*len(u), v
                if self.mode == "shape": return (), ()
                raise RuntimeError("failure")
        for mode in ["nan", "shape", "exception"]:
            with self.subTest(mode=mode):
                result = self.run_pulse(backend=Broken(mode))
                self.assertEqual(result.reason, "backend_failure")
                self.assertIsNone(result.proposal)

    def test_slow_backend_cannot_issue_late_proposal(self):
        clock = Clock()
        class Slow:
            def step(self, u, v, *args):
                clock.now += 30
                return u, v
        result = PulsePort(self.bundle, clock_ms=clock, backend=Slow()).pulse(self.frame, self.telemetry)
        self.assertEqual(result.reason, "deadline")
        self.assertIsNone(result.proposal)

    def test_unverified_backend_is_not_promoted(self):
        class Constant:
            def step(self, u, v, *args): return u, v
        result = self.run_pulse(backend=Constant())
        self.assertEqual(result.reason, "unverified_backend")
        self.assertIsNone(result.state_error_bound)
        self.assertIsNone(result.proposal)

    def test_oscillation_stops_at_value_cutoff(self):
        class Oscillate:
            def step(self, u, v, *args):
                return tuple(-1 if x >= 0 else 1 for x in u), v
        result = self.run_pulse(backend=Oscillate())
        self.assertEqual(result.reason, "insufficient_improvement_per_joule")
        self.assertLess(result.iterations, 128)

    def test_telemetry_failure_is_terminal(self):
        def broken(): raise RuntimeError("disconnected")
        result = PulsePort(self.bundle, clock_ms=Clock()).pulse(
            self.frame, self.telemetry, read_telemetry=broken)
        self.assertEqual(result.reason, "telemetry_or_clock_failure")
        self.assertIsNone(result.proposal)

    def test_invalid_frames_do_not_enter_computation(self):
        for values in [{"hazard": 0.1}, {**self.frame.values, "hazard": float("nan")},
                       {**self.frame.values, "contact": True}, {**self.frame.values, "extra": 0}]:
            with self.subTest(values=values):
                self.frame = Frame(1, 1000, values, 0.1)
                with self.assertRaises(ContractError): self.run_pulse()

    def test_artist_cannot_insert_controller_override(self):
        self.bundle["character"]["reserve_j"] = 0
        with self.assertRaises(ContractError): self.run_pulse()

    def test_configuration_snapshot_is_immutable_from_caller(self):
        baseline = self.run_pulse()
        port = PulsePort(self.bundle, clock_ms=Clock())
        self.bundle["character"]["bias"][0] = -1
        result = port.pulse(self.frame, self.telemetry)
        self.assertEqual(result.character_state, baseline.character_state)
        self.assertEqual(result.manifest_sha256, baseline.manifest_sha256)

    def test_hardware_and_quantum_modes_fail_explicitly(self):
        self.bundle["embodiment"]["mode"] = "hardware"
        with self.assertRaisesRegex(ContractError, "hardware"): self.run_pulse()
        self.bundle["embodiment"]["mode"] = "simulation"
        self.bundle["controller"]["backend"] = "qpu_async"
        with self.assertRaisesRegex(ContractError, "qpu_async"): self.run_pulse()

    def test_semantic_manifest_errors(self):
        original = deepcopy(self.bundle)
        mutations = [
            lambda b: b["emotions"]["graphs"][0]["nodes"][1].update(b=0),
            lambda b: b["emotions"]["graphs"][0]["nodes"][1].update(b=10),
            lambda b: b["emotions"]["graphs"][0]["edges"][0].update(target="missing"),
            lambda b: b["emotions"]["graphs"][0]["trigger"].update(sensor="missing"),
            lambda b: b["character"]["bias"].pop(),
            lambda b: b["controller"].update(character_coupling=1),
            lambda b: b["controller"].update(max_iterations=True),
            lambda b: b["controller"].update(action_j=-1),
        ]
        for i, change in enumerate(mutations):
            with self.subTest(case=i):
                self.bundle = deepcopy(original)
                change(self.bundle)
                with self.assertRaises(ContractError): validate_bundle(self.bundle)

    def test_generated_schemas_are_current(self):
        with tempfile.TemporaryDirectory() as d:
            export_schemas(d)
            for name in SCHEMAS:
                self.assertEqual((Path(d)/f"{name}.schema.json").read_text(),
                                 (ROOT/"schemas"/f"{name}.schema.json").read_text())

    def test_demo_result_reproducible_except_clock_origin(self):
        stored = json.loads((ROOT/"examples"/"normal-result.json").read_text())
        result = self.run_pulse()
        self.assertEqual(stored["iterations"], result.iterations)
        self.assertEqual(stored["proposal"]["velocity_m_s"], result.proposal["velocity_m_s"])
        self.assertEqual(stored["manifest_sha256"], result.manifest_sha256)


if __name__ == "__main__":
    unittest.main()
