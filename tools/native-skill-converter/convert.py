#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - startup guard
    raise SystemExit(
        "PyYAML is required for tools/native-skill-converter/convert.py. "
        "Install it with: python3 -m pip install -r tools/native-skill-converter/requirements.txt"
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[2]
TOOL_DIR = Path(__file__).resolve().parent


class ConversionError(RuntimeError):
    """Raised when the converter cannot prove a deterministic result."""


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConversionError(f"Expected YAML object in {path}")
    return data


def git_show(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT_DIR), "show", f"{commit}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ConversionError(
            f"Unable to read {relative_path} from commit {commit}: {stderr}"
        )
    return result.stdout


def relative_file_inventory(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    )


def source_file_inventory(root: Path) -> list[str]:
    return sorted(path.name for path in root.iterdir() if path.is_file())


def manifest_entry(manifest: dict, workflow_id: str) -> dict:
    workflows = manifest.get("workflows", [])
    if not isinstance(workflows, list):
        raise ConversionError("Manifest workflows must be a list")
    for entry in workflows:
        if entry.get("id") == workflow_id:
            if not isinstance(entry, dict):
                break
            return entry
    raise ConversionError(f"Workflow {workflow_id!r} is not present in the manifest")


def expected_legacy_files(entry: dict) -> list[str]:
    inventory = entry["legacy_inventory"]
    files = [
        inventory["workflow_file"],
        inventory["instructions_file"],
        inventory["template_file"],
    ]
    files.extend(inventory.get("data_files", []))
    files.extend(inventory.get("extra_files", []))
    return sorted(files)


def preserved_file_mappings(entry: dict) -> list[tuple[str, str]]:
    mappings = []
    for item in entry.get("preserve_files", []):
        if isinstance(item, str):
            mappings.append((item, item))
            continue
        if (
            isinstance(item, dict)
            and isinstance(item.get("source"), str)
            and isinstance(item.get("target"), str)
        ):
            mappings.append((item["source"], item["target"]))
            continue
        raise ConversionError("Manifest preserve_files entries must be strings or {source, target} objects")
    return mappings


def expected_generated_files(entry: dict) -> list[str]:
    target_dir = Path(entry["target_dir"])
    files = [(target_dir / relative_path).as_posix() for relative_path in entry["create_files"]]
    files.extend(
        (target_dir / target_relative_path).as_posix()
        for _, target_relative_path in preserved_file_mappings(entry)
    )
    return sorted(files)


def validate_agent_target(entry: dict) -> None:
    agent_yaml = load_yaml(ROOT_DIR / entry["agent_target"]["file"])
    menu = agent_yaml.get("agent", {}).get("menu", [])
    before_key = entry["agent_target"]["before_key"]
    before_value = entry["agent_target"]["before_value"]
    for menu_entry in menu:
        if (
            isinstance(menu_entry, dict)
            and menu_entry.get(before_key) == before_value
        ):
            return
    raise ConversionError(
        f"Agent target {before_key}: {before_value} not found in "
        f"{entry['agent_target']['file']}"
    )


def validate_module_help(entry: dict) -> None:
    module_help = ROOT_DIR / entry["module_help"]["file"]
    with module_help.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["code"] == entry["module_help"]["row_code"]:
                if row["workflow-file"] != entry["module_help"]["before_workflow_file"]:
                    raise ConversionError(
                        "module-help workflow-file does not match manifest before state "
                        f"for code {entry['module_help']['row_code']}"
                    )
                return
    raise ConversionError(
        f"module-help row {entry['module_help']['row_code']} not found in "
        f"{entry['module_help']['file']}"
    )


def validate_before_snapshot(entry: dict, snapshot: dict) -> None:
    source_dir = ROOT_DIR / entry["source_dir"]
    if not source_dir.is_dir():
        raise ConversionError(f"Missing source workflow directory: {source_dir}")

    expected_files = sorted(
        (source_dir / name).relative_to(ROOT_DIR).as_posix()
        for name in expected_legacy_files(entry)
    )
    if expected_files != snapshot["before"]["files"]:
        raise ConversionError(
            "Manifest legacy inventory does not match the seeded before snapshot"
        )

    actual_files = sorted(
        (source_dir / name).relative_to(ROOT_DIR).as_posix()
        for name in source_file_inventory(source_dir)
    )
    if actual_files != expected_files:
        raise ConversionError(
            "Legacy workflow inventory does not match the seeded before snapshot"
        )

    validate_agent_target(entry)
    validate_module_help(entry)


def validate_before_snapshot_contents(snapshot: dict) -> None:
    before_commit = snapshot["before"]["commit"]
    for relative_path in snapshot["before"]["files"]:
        actual_bytes = (ROOT_DIR / relative_path).read_bytes()
        expected_bytes = git_show(before_commit, relative_path)
        if actual_bytes != expected_bytes:
            raise ConversionError(
                f"Current source file does not match pinned before snapshot commit: {relative_path}"
            )


def validate_design_thinking_source(entry: dict, workflow_config: dict, instructions: str) -> None:
    expected_name = entry["id"]
    if workflow_config.get("name") != expected_name:
        raise ConversionError(
            f"Expected workflow name {expected_name!r}, found {workflow_config.get('name')!r}"
        )

    if workflow_config.get("description") is None:
        raise ConversionError("workflow.yaml is missing description")

    required_pairs = {
        "config_source": "{project-root}/_bmad/cis/config.yaml",
        "template": "{installed_path}/template.md",
        "instructions": "{installed_path}/instructions.md",
        "design_methods": "{installed_path}/design-methods.csv",
        "default_output_file": "{output_folder}/design-thinking-{{date}}.md",
    }
    for key, expected_value in required_pairs.items():
        actual = workflow_config.get(key)
        if actual != expected_value:
            raise ConversionError(
                f"Expected workflow.yaml {key}={expected_value!r}, found {actual!r}"
            )

    required_strings = [
        "<facilitation-principles>",
        "<workflow>",
        "<step n=\"1\" goal=\"Gather context and define design challenge\">",
        "<step n=\"7\" goal=\"Plan next iteration\">",
        "{design_methods}",
        "ABSOLUTELY NO TIME ESTIMATES",
        "CHECKPOINT PROTOCOL",
    ]
    for required in required_strings:
        if required not in instructions:
            raise ConversionError(
                f"Expected to find {required!r} in design-thinking instructions"
            )


def build_skill_manifest() -> str:
    return "type: skill\n"


def build_design_thinking_skill_md(skill_id: str, description: str, main_config: str) -> str:
    template = """---
name: __SKILL_ID__
description: '__DESCRIPTION__'
standalone: true
main_config: '__MAIN_CONFIG__'
---

# Design Thinking Skill

**Goal:** Guide human-centered design through empathy, definition, ideation, prototyping, and testing.

**Your Role:** You are a human-centered design facilitator. Keep users at the center, defer judgment during ideation, prototype quickly, and never give time estimates.

---

## INITIALIZATION

### Configuration Loading

Load config from `{main_config}` and resolve:

- `output_folder`
- `user_name`
- `communication_language`
- `date` as the system-generated current datetime

### Paths

- `resource_root` = `./resources`
- `skill_path` = `{project-root}/_bmad/cis/workflows/bmad-cis-design-thinking`
- `skill_manifest_file` = `{resource_root}/bmad-skill-manifest.yaml`
- `template_file` = `{resource_root}/template.md`
- `design_methods_file` = `{resource_root}/design-methods.csv`
- `default_output_file` = `{output_folder}/design-thinking-{date}.md`

### Inputs

- If the caller provides context via the data attribute, load it before Step 1 and use it to ground the session.
- Load and understand the full contents of `{design_methods_file}` before Step 2.
- Use `{template_file}` as the structure when writing `{default_output_file}`.

### Behavioral Constraints

- Do not give time estimates.
- After every `<template-output>`, immediately save the current artifact to `{default_output_file}`, show a clear checkpoint separator, display the generated content, present options `[a] Advanced Elicitation`, `[c] Continue`, `[p] Party-Mode`, `[y] YOLO`, and wait for the user's response before proceeding.

### Facilitation Principles

- Keep users at the center of every decision.
- Encourage divergent thinking before convergent action.
- Make ideas tangible quickly; prototypes beat discussion.
- Treat failure as feedback.
- Test with real users rather than assumptions.
- Balance empathy with momentum.

---

## EXECUTION

<workflow>

<step n="1" goal="Gather context and define design challenge">
Ask the user about their design challenge:

- What problem or opportunity are you exploring?
- Who are the primary users or stakeholders?
- What constraints exist (time, budget, technology)?
- What does success look like for this project?
- What existing research or context should we consider?

Load any context data provided via the data attribute.

Create a clear design challenge statement.

<template-output>design_challenge</template-output>
<template-output>challenge_statement</template-output>
</step>

<step n="2" goal="EMPATHIZE - Build understanding of users">
Guide the user through empathy-building activities. Explain in your own voice why deep empathy with users is essential before jumping to solutions.

Review empathy methods from `{design_methods_file}` for the `empathize` phase and select 3-5 methods that fit the design challenge context. Consider:

- Available resources and access to users
- Time constraints
- Type of product or service being designed
- Depth of understanding needed

Offer the selected methods with guidance on when each works best, then ask which methods the user has used or can use, or make a recommendation based on the specific challenge.

Help gather and synthesize user insights:

- What did users say, think, do, and feel?
- What pain points emerged?
- What surprised you?
- What patterns do you see?

<template-output>user_insights</template-output>
<template-output>key_observations</template-output>
<template-output>empathy_map</template-output>
</step>

<step n="3" goal="DEFINE - Frame the problem clearly">
<energy-checkpoint>
Check in: "We've gathered rich user insights. How are you feeling? Ready to synthesize them into problem statements?"
</energy-checkpoint>

Transform observations into actionable problem statements.

Guide the user through problem framing:

1. Create a Point of View statement: "[User type] needs [need] because [insight]"
2. Generate "How Might We" questions that open solution space
3. Identify key insights and opportunity areas

Ask probing questions:

- What's the real problem we're solving?
- Why does this matter to users?
- What would success look like for them?
- What assumptions are we making?

<template-output>pov_statement</template-output>
<template-output>hmw_questions</template-output>
<template-output>problem_insights</template-output>
</step>

<step n="4" goal="IDEATE - Generate diverse solutions">
Facilitate creative solution generation. Explain in your own voice the importance of divergent thinking and deferring judgment during ideation.

Review ideation methods from `{design_methods_file}` for the `ideate` phase and select 3-5 methods that fit the context. Consider:

- Group versus individual ideation
- Time available
- Problem complexity
- Team creativity comfort level

Offer the selected methods with brief descriptions of when each works best.

Walk through the chosen method or methods:

- Generate at least 15-30 ideas
- Build on others' ideas
- Go for wild and practical
- Defer judgment

Help cluster and select top concepts:

- Which ideas excite you most?
- Which ideas address the core user need?
- Which ideas are feasible given the constraints?
- Select 2-3 ideas to prototype

<template-output>ideation_methods</template-output>
<template-output>generated_ideas</template-output>
<template-output>top_concepts</template-output>
</step>

<step n="5" goal="PROTOTYPE - Make ideas tangible">
<energy-checkpoint>
Check in: "We've generated lots of ideas. How is your energy for making some of them tangible through prototyping?"
</energy-checkpoint>

Guide creation of low-fidelity prototypes for testing. Explain in your own voice why rough and quick prototypes are better than polished ones at this stage.

Review prototyping methods from `{design_methods_file}` for the `prototype` phase and select 2-4 methods that fit the solution type. Consider:

- Physical versus digital product
- Service versus product
- Available materials and tools
- What needs to be tested

Offer the selected methods with guidance on fit.

Help define the prototype:

- What's the minimum needed to test your assumptions?
- What are you trying to learn?
- What should users be able to do?
- What can you fake versus build?

<template-output>prototype_approach</template-output>
<template-output>prototype_description</template-output>
<template-output>features_to_test</template-output>
</step>

<step n="6" goal="TEST - Validate with users">
Design the validation approach and capture learnings. Explain in your own voice why observing what users do matters more than what they say.

Help plan testing:

- Who will you test with? Aim for 5-7 users.
- What tasks will they attempt?
- What questions will you ask?
- How will you capture feedback?

Guide feedback collection:

- What worked well?
- Where did they struggle?
- What surprised them, and you?
- What questions arose?
- What would they change?

Synthesize learnings:

- What assumptions were validated or invalidated?
- What needs to change?
- What should stay?
- What new insights emerged?

<template-output>testing_plan</template-output>
<template-output>user_feedback</template-output>
<template-output>key_learnings</template-output>
</step>

<step n="7" goal="Plan next iteration">
<energy-checkpoint>
Check in: "Great work. How is your energy for final planning and defining next steps?"
</energy-checkpoint>

Define clear next steps and success criteria.

Based on testing insights:

- What refinements are needed?
- What's the priority action?
- Who needs to be involved?
- What sequence makes sense?
- How will you measure success?

Determine the next cycle:

- Do you need more empathy work?
- Should you reframe the problem?
- Are you ready to refine the prototype?
- Is it time to pilot with real users?

<template-output>refinements</template-output>
<template-output>action_items</template-output>
<template-output>success_metrics</template-output>
</step>

</workflow>
"""
    return (
        template.replace("__SKILL_ID__", skill_id)
        .replace("__DESCRIPTION__", description)
        .replace("__MAIN_CONFIG__", main_config)
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def convert_design_thinking(entry: dict, output_root: Path) -> None:
    source_dir = ROOT_DIR / entry["source_dir"]
    target_dir = output_root / entry["target_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)

    workflow_config = load_yaml(source_dir / entry["legacy_inventory"]["workflow_file"])
    instructions = (source_dir / entry["legacy_inventory"]["instructions_file"]).read_text(
        encoding="utf-8"
    )
    validate_design_thinking_source(entry, workflow_config, instructions)

    description = workflow_config["description"]
    skill_id = entry["canonical_skill_id"]
    main_config = workflow_config["config_source"]

    for source_name, target_relative_path in preserved_file_mappings(entry):
        destination = target_dir / target_relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_dir / source_name, destination)

    write_text(
        target_dir / "SKILL.md",
        build_design_thinking_skill_md(skill_id, description, main_config),
    )
    write_text(target_dir / "resources" / "bmad-skill-manifest.yaml", build_skill_manifest())


def compare_generated_to_snapshot(entry: dict, output_root: Path, snapshot: dict) -> None:
    expected_files = expected_generated_files(entry)
    if expected_files != snapshot["after"]["files"]:
        raise ConversionError(
            "Manifest generated inventory does not match the seeded after snapshot"
        )

    actual_files = relative_file_inventory(output_root)
    if actual_files != expected_files:
        raise ConversionError(
            "Generated file inventory does not match the seeded after snapshot"
        )

    fixture_root = ROOT_DIR / snapshot["after"]["generated_fixture_root"]
    fixture_files = relative_file_inventory(fixture_root)
    if fixture_files != snapshot["after"]["generated_files"]:
        raise ConversionError(
            "Seeded generated-file fixtures do not match the after snapshot"
        )

    for relative_path in snapshot["after"]["generated_files"]:
        actual_bytes = (output_root / relative_path).read_bytes()
        expected_bytes = (fixture_root / relative_path).read_bytes()
        if actual_bytes != expected_bytes:
            raise ConversionError(
                f"Generated file does not match seeded after snapshot: {relative_path}"
            )

    source_dir = ROOT_DIR / entry["source_dir"]
    target_dir = Path(entry["target_dir"])
    for source_name, target_relative_path in preserved_file_mappings(entry):
        actual_bytes = (output_root / target_dir / target_relative_path).read_bytes()
        expected_bytes = (source_dir / source_name).read_bytes()
        if actual_bytes != expected_bytes:
            raise ConversionError(
                "Preserved runtime companion does not match the current source file: "
                f"{target_dir / target_relative_path}"
            )


def build_output_root(path_arg: str | None) -> Path:
    if path_arg:
        path = Path(path_arg).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(tempfile.mkdtemp(prefix="cis-native-skill-converter-"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic native-skill converter prototype for CIS workflows."
    )
    parser.add_argument("--workflow", required=True, help="Workflow id from manifest.yaml")
    parser.add_argument(
        "--manifest",
        default=str(TOOL_DIR / "manifest.yaml"),
        help="Path to the converter manifest",
    )
    parser.add_argument(
        "--output-dir",
        help="Output root for generated files. Defaults to a new temp directory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the current source against the pinned before snapshot commit and compare the generated output to the seeded after snapshot files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    manifest = load_yaml(Path(args.manifest))
    entry = manifest_entry(manifest, args.workflow)

    if entry["id"] != "design-thinking":
        raise ConversionError(
            "This prototype only supports the seeded design-thinking workflow for now"
        )

    if entry.get("profile") != manifest["defaults"]["standard_profile"]:
        raise ConversionError(
            f"Unsupported profile for prototype converter: {entry.get('profile')!r}"
        )

    snapshot = load_yaml(ROOT_DIR / entry["seeded_snapshot"]["file"])
    validate_before_snapshot(entry, snapshot)
    if args.check:
        validate_before_snapshot_contents(snapshot)

    output_root = build_output_root(args.output_dir)
    convert_design_thinking(entry, output_root)

    if args.check:
        compare_generated_to_snapshot(entry, output_root, snapshot)

    print(f"workflow={entry['id']}")
    print(f"output_root={output_root}")
    if args.check:
        print("check=passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
