# barclays-buk-reverse-spec-generator-reverse-spec-generator-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-reverse-spec-generator-reverse-spec-generator-agent-v1` |
| Plugin name | `barclays-buk-reverse-spec-generator` |
| Component type | agent-plugin |
| Owner | Preetha Ramaswamy |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-reverse-spec-generator@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- ACTION (required): One of `generate-spec`, `amend`, `converge`, `generate-tests`, or `implement`
- SOURCE_PATH (required for `generate-spec`, optional for others): Path to source code file(s) or directory; supports Python, Java, and JavaScript/TypeScript
- SPEC_PATH (required for `amend`, `converge`, `generate-tests`, `implement`): Path to the existing `.spec` YAML file
- OUTPUT_PATH (optional): Where to write outputs; defaults to the same directory as SPEC_PATH or SOURCE_PATH
- FRAMEWORK (optional): Test framework override — `junit5`, `pytest`, or `jest`; auto-detected from build files if omitted
- LANGUAGE (optional): Language override — `python`, `java`, or `javascript`; auto-detected from file extension if omitted
- OPTIONS (optional): Key=value pairs, e.g. `confidence_threshold=0.6 include_private=false`

## Preconditions

- SOURCE_PATH must point to a readable source code file or directory containing `.py`, `.java`, `.ts`, `.js`, or `.kt` files when ACTION is `generate-spec`
- SPEC_PATH must point to an existing, valid BDD YAML `.spec` file when ACTION is `amend`, `converge`, `generate-tests`, or `implement`
- `barclays-buk-reverse-spec-generator:bdd-specification`, `spec-generation-patterns`, and `convergence-loop` skills must be available; placeholder skills are reported in Flags
- The spec validator must be accessible at `plugins/tooling/barclays-buk-reverse-spec-generator/validator/spec-check.py`
- OUTPUT_PATH directory must be writable

## Expected outputs

- `OUTPUT_PATH/<module>.spec`: Generated or amended BDD YAML specification file (for `generate-spec` and `amend`)
- `OUTPUT_PATH/<module>.convergence.yaml`: Persistent convergence loop state tracking alignment, divergence, and source_of_truth per behavior (for `converge` and `implement`)
- `OUTPUT_PATH/tests/`: Generated test files organised by section — behaviors, rules, constraints, integration (for `generate-tests`)
- `OUTPUT_PATH/stubs/`: Language-appropriate code stubs for spec-led missing or diverged behaviors (for `implement`)
- A formatted convergence report or stub generation summary printed to the agent response
- A `## Flags` section in the response reporting placeholder skills, missing inputs, and decisions made under uncertainty

## Exclusions

- Does NOT execute the generated tests — test execution is the caller's responsibility
- Does NOT write directly to the TARGET source code files; stubs are written to a separate `stubs/` directory
- Does NOT generate specifications from scratch without source code to analyze
- Does NOT generate stubs for behaviors where `source_of_truth` is `code` or `unknown`
- Does NOT enforce workflow sequencing — the caller decides the order of actions

## Verification

For `generate-spec`: verify that `OUTPUT_PATH/<module>.spec` exists and contains YAML-structured entities, behaviors, rules, and constraints with confidence scores. Run `python plugins/tooling/barclays-buk-reverse-spec-generator/validator/spec-check.py <spec_path>` and confirm it exits with zero errors. For `converge`: verify that `<module>.convergence.yaml` exists and contains per-behavior `divergence_status` and `convergence_pct` fields. For `generate-tests`: verify that test files appear under `OUTPUT_PATH/tests/` and that the post-test validator reports a non-zero passing count. For `implement`: verify that stub files appear under `OUTPUT_PATH/stubs/` and that `.convergence.yaml` shows `implementation_status: stub_generated` for the relevant behaviors.
