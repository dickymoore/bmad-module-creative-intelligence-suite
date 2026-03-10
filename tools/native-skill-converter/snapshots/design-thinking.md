# Design Thinking Reference Snapshot

This snapshot is limited to the converter-managed surface.

- before_ref: `origin/main`
- after_ref: `b3a0101`
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
src/workflows/bmad-cis-design-thinking/bmad-skill-manifest.yaml
src/workflows/bmad-cis-design-thinking/design-methods.csv
src/workflows/bmad-cis-design-thinking/template.md
src/workflows/bmad-cis-design-thinking/workflow.md
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
A src/workflows/bmad-cis-design-thinking/bmad-skill-manifest.yaml
A src/workflows/bmad-cis-design-thinking/workflow.md
D src/workflows/design-thinking/README.md
D src/workflows/design-thinking/instructions.md
D src/workflows/design-thinking/workflow.yaml
```

## Notes

- The real slice also updated maintainer docs outside the converter-managed surface.
- Those extra docs changes are intentionally excluded from this snapshot so a future converter can stay lean and deterministic.
