# Deterministic Native Skill Converter Proposal

## Goal

Define a small, fail-closed converter that can reproduce approved CIS native-skill conversions without guessing.

This branch is idea-only. It does not convert any workflows.

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
- some workflows use `workflow:` in the agent menu while others already use `exec:`
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
5. Preserve the runtime companion files listed in the manifest, byte-for-byte.
6. Synthesize `SKILL.md` from canonical id and approved description text.
7. Synthesize `bmad-skill-manifest.yaml` with `type: skill`.
8. Synthesize `workflow.md` by merging `workflow.yaml` and `instructions.md` using the manifest profile:
   - move config loading into initialization
   - convert installed-path references to skill-local references where appropriate
   - keep behavioral constraints
   - drop loader/runner scaffolding
9. Delete legacy entry files only if the manifest says to delete them.
10. Rewrite only the allowlisted external references:
   - agent menu target
   - `module-help.csv` workflow-file value
   - explicitly listed repo-internal notes/docs if approved
11. Emit a normalized before/after snapshot for verification.
12. Stop if any produced file set or rewritten value differs from the manifest and snapshot expectations.

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
- after ref: `feature/native-skills-design-thinking-first-slice` at `b3a0101281ad46fe68754c3992e2c174c5af2a02`

The converter prototype should use that pair to prove the snapshot approach before attempting other workflows.

## Open Question: Normalize To `exec:` Or Preserve Existing Field Shapes

The future converter still needs an explicit policy for agent menu rewrites.

Current situation:

- `design-thinking`, `innovation-strategy`, and `problem-solving` currently point to legacy workflows through `workflow:`
- `storytelling` already uses `exec:`
- the converted design-thinking slice now uses `exec:` to point at `SKILL.md`

Decision still needed:

- normalize all converted agent menu entries to `exec:` for consistency with the native-skill entrypoint
- or preserve loader-compatible field shapes where they already differ and only rewrite the target value

This should be decided before implementation because it affects:

- the manifest schema
- the expected after snapshots
- whether mixed field shapes are considered valid converter output

## Out Of Scope For This Idea Branch

- implementing the converter
- converting `innovation-strategy`, `problem-solving`, or `storytelling`
- changing the existing design-thinking PR branch
- broad CIS docs cleanup
