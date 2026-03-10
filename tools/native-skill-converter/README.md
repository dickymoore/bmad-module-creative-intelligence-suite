# Native Skill Converter Prototype

This directory contains a manifest-driven deterministic converter prototype for CIS native-skill packaging.

Current executable:

- `python3 tools/native-skill-converter/convert.py`

Python requirement:

- `python3 -m pip install -r tools/native-skill-converter/requirements.txt`

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
- `convert.py`
  - fail-closed prototype runner
  - currently supports only the seeded `design-thinking` case
  - generates into a temp or explicit output directory without mutating the working tree
- `snapshots/`
  - normalized before/after reference state for seeded workflows
  - used to prove deterministic output

## Non-Goals

- no smart discovery
- no generic repo-wide conversion
- no guessing from folder names or descriptions
- no conversion of workflows not listed in the manifest

## Current Scope

The current prototype is intentionally narrow:

- supported workflow id: `design-thinking`
- supported profile: `cis-legacy-workflow-to-native-skill`
- output mode: generated files only, outside the working tree by default
- verification mode: compare generated output to the pinned seeded reference commit

Other manifest entries remain declarative only.

## Usage

Generate the seeded native-skill package into a temp directory:

```text
python3 tools/native-skill-converter/convert.py --workflow design-thinking
```

Generate and verify it against the seeded reference snapshot and commit:

```text
python3 tools/native-skill-converter/convert.py --workflow design-thinking --check
```

Generate into an explicit output directory:

```text
python3 tools/native-skill-converter/convert.py --workflow design-thinking --check --output-dir /tmp/cis-converter-out
```

## Expected Future Shape

The current runner already takes one workflow id and fails closed unless:

- the source inventory matches the manifest exactly
- the current external references match the manifest exactly
- the produced output matches the expected seeded reference output when `--check` is used

## Snapshot Idea

The seeded snapshot for `design-thinking` ties together:

- the before state on `origin/main`
- the approved after state from the separate reference branch

That reference lets a future converter prove:

- which files are renamed, deleted, preserved, and created
- which external references are rewritten
- which outputs are synthesized rather than copied

If future workflows need different rules, the manifest should add a new explicit profile instead of expanding generic logic.
