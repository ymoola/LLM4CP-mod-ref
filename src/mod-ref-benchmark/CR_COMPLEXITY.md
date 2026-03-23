# CR Complexity Metadata

This document defines the simplified manual `complexity` metadata stored in each CR `desc.json` under `src/mod-ref-benchmark/problems/*/CR*/desc.json`.

## Purpose

The metadata measures **model-edit hardness**, not runtime hardness.

It is intentionally compact. The goal is to keep only the fields that are useful for benchmark analysis and easy to maintain as new CRs are added.

## Schema

Each CR `desc.json` stores:

```json
"complexity": {
  "difficulty_label": "medium",
  "difficulty_rationale": "Short explanation of why this CR is low/medium/high.",
  "change_types": {
    "constraints": "add",
    "decision_variables": "none",
    "objective": "none"
  },
  "base_model": {
    "decision_variable_count": 60,
    "constraint_count": 88
  },
  "cr_impact": {
    "affected_decision_variables": 10,
    "affected_constraints": 6,
    "notes": "Touches the sequence variable and adds one sliding-window constraint family."
  }
}
```

## Field meanings

### `difficulty_label`
- `low`: localized change, usually one direct add/modify/remove to an existing model component
- `medium`: broader change that touches multiple windows/pairs/groups or changes the objective, but stays within the same model architecture
- `high`: structural change that adds/removes decision-variable families, introduces optionality or helper-variable tracking, or combines major constraint and objective changes

### `difficulty_rationale`
A short human-written explanation of why the CR was labeled low/medium/high.

### `change_types`
- `constraints`: whether the CR adds, modifies, removes, or mixes constraint families
- `decision_variables`: whether the CR adds, modifies, removes, or mixes decision-variable families
- `objective`: whether the CR adds, modifies, removes, or leaves the objective unchanged

### `base_model`
- `decision_variable_count`: total scalar decision variables in the base model for the CR's shipped `input_data.json`
- `constraint_count`: total scalar constraints in the base model for the same shipped instance

### `cr_impact`
- `affected_decision_variables`: scalar decision variables directly touched by the CR
- `affected_constraints`: scalar constraints directly added/modified/removed by the CR
- `notes`: short text naming the main variable families and/or constraint groups touched by the CR

## Counting rules

- Counts are concrete instance counts for the CR's shipped `input_data.json`.
- `base_model` always refers to the unmodified `base/reference_model.py`.
- `cr_impact` always refers to the part of the model directly changed by the CR relative to the base model.
- Hardness is based on modeling scope and structural impact, not solver runtime.

## Controlled values

- `difficulty_label`: `low | medium | high`
- `change_types.constraints`: `none | add | modify | remove | mixed`
- `change_types.decision_variables`: `none | add | modify | remove | mixed`
- `change_types.objective`: `none | add | modify | remove | mixed`
