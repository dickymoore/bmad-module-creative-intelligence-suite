# Native Skill Converter Prototype

This directory is scaffold only.

It defines a manifest-driven prototype surface for a future deterministic CIS native-skill converter. No converter implementation lives here yet.

## Intent

Use explicit manifests and snapshots to convert only known CIS workflows from:

- `workflow.yaml` + `instructions.md`

to:

- canonical `type: skill` directories with `SKILL.md` and `workflow.md`

## Prototype Surface

- `manifest.yaml`
  - authoritative workflow inventory
  - canonical ids
  - conversion profiles
  - allowed external rewrites
  - exception flags
- `snapshots/`
  - normalized before/after reference state for seeded workflows
  - used to prove deterministic output

## Non-Goals

- no smart discovery
- no generic repo-wide conversion
- no guessing from folder names or descriptions
- no conversion of workflows not listed in the manifest

## Expected Future Shape

A future implementation should take one workflow id and fail closed unless:

- the source inventory matches the manifest exactly
- the current external references match the manifest exactly
- the produced output matches the expected normalized snapshot shape

Example future CLI surface:

```text
node tools/native-skill-converter/run.mjs --workflow design-thinking
```

That command is intentionally not implemented on this branch.

## Snapshot Idea

The seeded snapshot for `design-thinking` ties together:

- the before state on `origin/main`
- the approved after state from the separate reference branch

That reference lets a future converter prove:

- which files are renamed, deleted, preserved, and created
- which external references are rewritten
- which outputs are synthesized rather than copied

If future workflows need different rules, the manifest should add a new explicit profile instead of expanding generic logic.
