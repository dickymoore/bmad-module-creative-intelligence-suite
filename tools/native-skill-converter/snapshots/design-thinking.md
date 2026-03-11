# Design Thinking Reference Snapshot

This snapshot is limited to the converter-managed surface.

- before_ref: `origin/main`
- after_label: `design-thinking-simple-skill`
- canonical_skill_id: `bmad-cis-design-thinking`

## Before Workflow Inventory

```text
src/workflows/design-thinking/README.md
src/workflows/design-thinking/design-methods.csv
src/workflows/design-thinking/instructions.md
src/workflows/design-thinking/template.md
src/workflows/design-thinking/workflow.yaml
```

## After Workflow Inventory

```text
src/workflows/bmad-cis-design-thinking/SKILL.md
src/workflows/bmad-cis-design-thinking/resources/bmad-skill-manifest.yaml
src/workflows/bmad-cis-design-thinking/resources/design-methods.csv
src/workflows/bmad-cis-design-thinking/resources/template.md
```

## Agent Menu Rewrite

Before:

```yaml
- trigger: DT or fuzzy match on design-thinking
  workflow: "{project-root}/_bmad/cis/workflows/design-thinking/workflow.yaml"
```

After:

```yaml
- trigger: DT or fuzzy match on design-thinking
  exec: "{project-root}/_bmad/cis/workflows/bmad-cis-design-thinking/SKILL.md"
```

## Module Help Rewrite

Before:

```text
DT,...,_bmad/cis/workflows/design-thinking/workflow.yaml,bmad-cis-design-thinking,...,design-thinking-coach,...
```

After:

```text
DT,...,skill:bmad-cis-design-thinking,bmad-cis-design-thinking,...,design-thinking-coach,...
```

## Managed Path Diff

```text
M src/agents/design-thinking-coach.agent.yaml
M src/module-help.csv
A src/workflows/bmad-cis-design-thinking/SKILL.md
A src/workflows/bmad-cis-design-thinking/resources/bmad-skill-manifest.yaml
A src/workflows/bmad-cis-design-thinking/resources/design-methods.csv
A src/workflows/bmad-cis-design-thinking/resources/template.md
D src/workflows/design-thinking/README.md
D src/workflows/design-thinking/instructions.md
D src/workflows/design-thinking/workflow.yaml
```

## Notes

- The current preferred mold is the simple-skill layout: root `SKILL.md`, no root redirect, and runtime companions under `resources/`.
- The seeded fixture files cover synthesized outputs only. Preserved runtime companions are verified byte-for-byte from the pinned before-state source once the converter proves the source still matches `origin/main`.
- Maintainer-doc fallout remains intentionally excluded from the converter-managed surface so the branch stays lean and deterministic.
