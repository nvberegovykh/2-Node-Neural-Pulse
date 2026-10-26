# Artist's guide to a Neural Pulse character

Start with the four example files. The runtime reads them together and rejects mismatched axes, missing sensors, malformed graphs, and unsupported fields.

## Character

Edit `examples/character.json`:

```json
{
  "schema_version": "0.1.0",
  "id": "observer-curious",
  "name": "Curious Observer",
  "axes": ["caution", "curiosity", "engagement"],
  "bias": [0.2, 0.4, 0.15],
  "description": "Artist-authored example: explore novelty while retaining caution."
}
```

`bias[j]` corresponds to `axes[j]`. The labels carry your artistic interpretation. Their numerical behavior comes from the recurrence and mappings. Changing the number or meaning of axes requires coordinated engineering changes to sensor and action mappings.

## Emotion graphs

A graph activates when its sensor crosses its configured threshold. For example, novelty of at least `0.5` activates the curiosity graph. It contains:

```json
{
  "id": "curiosity",
  "trigger": {"sensor": "novelty", "gte": 0.5},
  "nodes": [
    {"id": "interest", "axis": "curiosity", "a": 0.7, "b": 0},
    {"id": "approach", "axis": "engagement", "a": 0.2, "b": 1}
  ],
  "edges": [
    {"source": "interest", "target": "approach", "weight": 0.2}
  ]
}
```

When active, `interest` contributes `0.7` to curiosity and `approach` becomes `0.2 + 0.2×0.7 = 0.34`. When inactive, both output slots are zero. The second example graph uses slots 2 and 3, so the full sequence always has four slots.

Use negative weights for inhibitory relationships. Every edge must name vertices in its own graph. Duplicate vertices, duplicate edges, dangling edges, and duplicate `b` positions are rejected. `b` values must cover `0..M-1` across all M vertices. If you remove a vertex, update downstream slot references and version the bundle.

## Artist versus equipment settings

| Authored data | Ownership in the proposed workflow |
|---|---|
| Character name, description and biases | Artist |
| Emotion names, intensities, relationships, triggers and slots | Artist, validated against the approved sensor/axis contract |
| Body geometry and accessible manipulators | Equipment integrator |
| Sensor normalization and units | Equipment integrator |
| Power reserve, heat, overload, speed, and deadlines | Equipment integrator |
| Runtime permissions and accepted bundle version | Operator / supervisor |

These are workflow boundaries, not operating-system access controls. v0.1 loads local JSON; anyone who can edit the controller file can change its values. Production requires authenticated configuration, restricted writes and approval/version policies outside this library. The hash identifies a bundle; it is not a signature.

## Preview an edit

```bash
python -m neural_pulse validate
python -m neural_pulse demo --output pulse-result.json
python -m unittest discover -s tests -v
```

The checked-in replay test intentionally detects changes to the example manifest. If you revise the example intentionally, regenerate `examples/normal-result.json`, inspect the behavioral change, then run the tests again. A separate character can live in a new folder containing all four files, selected with `--config path/to/folder`.

Schemas in `schemas/` support editor validation. The runtime also checks cross-file meanings that JSON Schema alone does not express here, including matrix dimensions, slot continuity and graph references. Regenerate schemas with `python -m neural_pulse schemas` after changing the contract code.

The schema accepts embodiment categories `organic`, `synthetic` and `cybernetic`. All executable examples remain in `simulation` mode. Changing the category describes intent; it does not create a biological or hardware interface.
