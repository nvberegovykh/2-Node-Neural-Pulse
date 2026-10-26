"""Run from the repository root: python -m neural_pulse demo."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .contracts import export_schemas, load_bundle
from .engine import Frame, PulsePort, Telemetry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "validate", "schemas"])
    parser.add_argument("--config", default="examples")
    parser.add_argument("--scenario", choices=["normal", "hazard", "low-energy", "thermal", "uncertain"], default="normal")
    parser.add_argument("--output", help="Write JSON to this path; no hardware output")
    args = parser.parse_args()
    if args.command == "schemas":
        export_schemas("schemas")
        print("Exported JSON Schema contracts")
        return
    bundle = load_bundle(args.config)
    if args.command == "validate":
        print("Valid manifests and cross-file references")
        return
    # Deterministic virtual clock; numbers are simulation inputs, not measurements.
    now = [1000.0]
    def clock():
        now[0] += 0.01
        return now[0]
    scenario = args.scenario
    frame = Frame(1, 1000, {"hazard": 0.95 if scenario == "hazard" else 0.1,
                           "novelty": 0.8, "contact": 0.2},
                  0.8 if scenario == "uncertain" else 0.1)
    telemetry = Telemetry(11 if scenario == "low-energy" else 100,
                          85 if scenario == "thermal" else 35, 0.05)
    result = PulsePort(bundle, clock_ms=clock).pulse(frame, telemetry)
    output = json.dumps(asdict(result), indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
