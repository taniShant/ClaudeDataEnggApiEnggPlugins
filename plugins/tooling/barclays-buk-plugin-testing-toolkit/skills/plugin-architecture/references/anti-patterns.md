# Plugin Architecture Anti-Patterns

Flag these when supported by repository evidence.

## Giant Agent Prompt
Reusable knowledge, detailed procedures, policies, examples, and orchestration all embedded in one agent definition.

## Micro-Agent Proliferation
Separate agents created for every task despite no meaningful persona/context/tool boundary.

## Persona Without Isolation Need
Subagent exists only because it sounds like an expert role; a Skill would provide the expertise without isolated execution.

## Skill as Hardcoded Answer Book
Skill contains project-specific solutions and numeric/product prescriptions instead of principles and decision criteria.

## Accidental Universal Rule
A conclusion from one project/task becomes MUST behaviour for all repositories.

## Prompt-as-Enforcement
Critical invariant exists only as prose even though deterministic enforcement is required and available.

## LLM-as-Parser
Claude repeatedly performs deterministic parsing/validation/transformation better handled by code.

## Business Logic in MCP
Connectivity/tool layer owns substantial reasoning/methodology that should live in Skill/Agent/workflow.

## Fixed Pipeline for Dynamic Problem
Hardcoded sequence cannot adapt to evidence and causes irrelevant/incorrect stages.

## Dynamic Agent for Deterministic Pipeline
LLM repeatedly decides an objective fixed sequence, increasing cost and variability.

## Skill Fan-Out at Workflow Scale
Skill manually coordinates large numbers of subagents when orchestration should be codified as a Dynamic Workflow.

## Workflow for Tiny Task
Dynamic Workflow introduced where a simple Skill or a couple of subagents are sufficient.

## Agent Team for Embarrassingly Parallel Work
Peers do not need collaboration; fan-out/fan-in workflow or subagents would be simpler.

## Knowledge Duplication
Same standards/methodology copied into agents, skills, commands, and workflows.

## Early Context Loading
Large references/examples always loaded although rarely needed.

## Configuration Masquerading as Expertise
Environment/project values embedded in reusable Skill or Agent instructions.

## Missing Termination
Iterative workflow lacks max iterations, success condition, or no-progress detection.

## Missing Verification
Expert component produces recommendations without checking them against requirements/evidence.
