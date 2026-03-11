# Deterministic Native Skill Converter Proposal

## Goal

Define a small, fail-closed converter that can reproduce approved CIS native-skill conversions without guessing.

This branch is prototype-only. It does not mutate repo workflows in place; the converter generates and checks deterministic output outside the working tree.

## Current Thread Steer

The current native-skills thread changes the target mold from the first converted PR shape.

Direction now encoded by this prototype:

- for simple skills like `design-thinking`, keep the prompt directly in root `SKILL.md`
- do not use a root `SKILL.md` -> `workflow.md` redirect for the seeded simple case
- keep only `SKILL.md` at skill root
- place the skill manifest and runtime companions under `resources/`
- normalize converted agent menu entries to `exec:`
- keep converter validation narrow and attached to real conversions rather than building a separate validator project

Implication:

- the existing `feature/native-skills-design-thinking-first-slice` branch remains useful source material, but it is no longer the preferred final mold for the converter prototype because it still reflects the intermediate `SKILL.md` + `workflow.md` layout

## Why This Is Feasible

The remaining CIS-native workflows share a constrained source shape:

- one workflow directory per capability
- a legacy `workflow.yaml` entrypoint
- a matching `instructions.md`
- one `template.md`
- one workflow-local CSV data file
- one agent/menu entry and one `module-help.csv` row

That makes deterministic conversion realistic for:

- `design-thinking`
- `innovation-strategy`
- `problem-solving`
- `storytelling`

## Why It Should Be Manifest-Driven, Not Generic

The converter should not try to infer intent from arbitrary workflow folders.

Reasons:

- the mechanical file shape is similar, but the external wiring is not identical
- some workflows currently use `workflow:` in the agent menu while others already use `exec:`
- some workflows can use a standard conversion profile while others need explicit exception handling
- repo-internal follow-up edits should be allowlisted, not discovered heuristically
- deterministic output requires an explicit source inventory, target inventory, and rewrite list

The manifest should therefore be the authority for:

- which workflows are supported
- which files are expected before conversion
- which files must exist after conversion
- which external references may be rewritten
- which workflows are blocked pending a special profile

If a workflow does not match its manifest entry exactly, the converter should stop.

## Exact Mechanical Steps To Automate

For a supported standard CIS workflow, the converter should:

1. Read the manifest entry for one workflow id.
2. Validate the exact legacy source inventory.
3. Validate the exact agent/menu target and `module-help.csv` row before any edits.
4. Rename the workflow directory to the canonical skill id.
5. Preserve the runtime companion files listed in the manifest, byte-for-byte, under `resources/`.
6. Synthesize root `SKILL.md` by merging `workflow.yaml` and `instructions.md` using the manifest profile:
   - keep the prompt directly in `SKILL.md` for the simple seeded case
   - move config loading into initialization
   - convert installed-path references to `resources/` paths where appropriate
   - keep behavioral constraints
   - drop legacy loader/runner scaffolding
7. Synthesize `resources/bmad-skill-manifest.yaml` with `type: skill`.
8. Delete legacy entry files only if the manifest says to delete them.
9. Rewrite only the allowlisted external references:
   - agent menu target
   - `module-help.csv` workflow-file value
   - explicitly listed repo-internal notes/docs if approved
10. Emit a normalized before/after snapshot for verification.
11. Stop if any produced file set or rewritten value differs from the manifest and snapshot expectations.

## Known Exceptions Already Found

### Standard-profile candidates

- `design-thinking`
- `innovation-strategy`
- `problem-solving`

These all follow the same five-file legacy workflow shape and use direct agent `workflow:` wiring.

### Storytelling exception profile

`storytelling` should not be treated as a generic clone of the others.

Known differences:

- the agent lives under a nested path: `src/agents/storyteller/storyteller.agent.yaml`
- the agent is a sidecar agent with persistent memory files
- the agent already uses `exec:` instead of `workflow:`
- sidecar memory files exist under `src/agents/storyteller/storyteller-sidecar/`
- the workflow variable names differ slightly from the data filename (`story_frameworks` vs `story-types.csv`)

That does not make deterministic conversion impossible, but it does require a separate manifest profile with explicit rules.

## Validation Proposal

The converter should be proven with snapshots, not by eyeballing diffs.

Proposed validation loop:

1. Capture a normalized before snapshot from a known source ref.
2. Run the converter.
3. Capture a normalized after snapshot from the working tree.
4. Compare that result to an approved after snapshot or approved reference commit.

The snapshot should at minimum include:

- workflow directory file inventory
- deleted legacy files
- created skill files
- preserved companion files
- agent target key/value before and after
- `module-help.csv` workflow-file before and after
- any explicitly allowed repo-internal reference edits

Deterministic means:

- no LLM involvement
- no fuzzy matching
- no opportunistic repo-wide rewrites
- the same manifest entry yields the same normalized output every time

## Seed Reference

`design-thinking` is included in the manifest as the seeded reference conversion.

Reason:

- we already have a real converted result on a separate branch
- that branch provides a concrete approved target shape instead of a hypothetical one

Reference:

- before ref: `origin/main` at `131768fbf9b843ce8dfd2ed75556f366eb3e6d9d`
- after label: `design-thinking-simple-skill`

The converter prototype should use that pinned before ref plus the committed after fixtures to prove the snapshot approach before attempting other workflows.

## Decision: Normalize Converted Agent Menu Entries To `exec:`

The converter now treats `exec:` as canonical for native-skill entrypoints.

Why this is the chosen direction:

- `design-thinking`, `innovation-strategy`, and `problem-solving` currently point to legacy workflows through `workflow:`
- `storytelling` already uses `exec:`
- the active BMAD direction is to execute native skills through `exec` rather than keep mixed legacy command shapes
- a single canonical field makes the manifest and expected after snapshots structurally uniform

Why this matters:

- without a fixed rewrite policy, the converter could produce functionally correct but structurally mixed output
- that would weaken the deterministic claim and make snapshot approval harder across workflows

## Decision: Snapshot Scope Stays On The Converter-Managed Surface

The seeded snapshots intentionally cover only:

- workflow directory file inventory
- preserved runtime companions
- synthesized skill files
- agent target rewrite
- `module-help.csv` rewrite
- explicitly allowlisted repo-internal references when needed

Why this is the chosen boundary:

- it keeps the converter lean
- it avoids turning packaging into general repo documentation maintenance
- it lets deterministic checks fail only on surfaces the converter actually owns

Implication:

- maintainer-doc fallout can still be noted, but it should not be folded into the deterministic converter unless it gets its own explicit allowlist rules

## Decision: First Implementation Scope Is `design-thinking` Only

The executable runner intentionally supports only the seeded `design-thinking` case.

Why this is the chosen first cut:

- it is the smallest verified CIS-native workflow
- it already has a real converted slice to learn from
- it lets the branch prove the manifest model and snapshot model before taking on additional profiles

Implication:

- `innovation-strategy` and `problem-solving` remain declarative manifest entries until the standard profile is proven stable
- `storytelling` stays blocked behind an explicit exception profile

## Out Of Scope For This Idea Branch

- implementing the converter
- converting `innovation-strategy`, `problem-solving`, or `storytelling`
- changing the existing design-thinking PR branch
- broad CIS docs cleanup
