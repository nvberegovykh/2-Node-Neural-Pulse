# Contributing

Run the reference from the repository root with Python 3.10+:

```bash
python -m neural_pulse validate
python -m unittest discover -s tests -v
```

No dependency installation is required. The implementation was exercised on Python 3.12.14; additional Python versions are not yet tested.

For contract changes, edit `neural_pulse/contracts.py`, regenerate with `python -m neural_pulse schemas`, and update affected examples. Preserve explicit versioning and document changes to `a`, `b`, axis order, units, and terminal conditions.

For model changes, add tests that distinguish actual behavior from internal numerical stability. A faster demo is not enough to claim real-time execution; provide target hardware and scheduling evidence. Do not substitute simulated energy values for measurements.

Keep vendor integrations and remote compute opt-in. The default commands must remain offline and simulation-only. Never add secrets, credentials, personal telemetry, or live neural/actuator access to example manifests.
