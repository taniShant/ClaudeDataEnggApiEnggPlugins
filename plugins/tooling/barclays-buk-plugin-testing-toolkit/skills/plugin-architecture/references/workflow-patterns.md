# Workflow and Orchestration Patterns

Classify workflows by both CONTROL MODEL and PATTERN.

## Control model

### STATIC
Sequence is known and should execute predictably.

### DYNAMIC
Next action depends materially on reasoning/intermediate findings.

### HYBRID
High-level routing is dynamic while individual stages are deterministic or codified. Often the best architecture.

## Pattern catalogue

### Fan-out / Fan-in
One input becomes many independent work items processed concurrently, then aggregated.

Use when items are independent and synthesis is required.

Strong Dynamic Workflow candidate at large scale.

### Classify & Act
Classify input/work item, route it to the appropriate specialist/capability, then combine or return results.

Use when different input classes require materially different treatment.

Classifier may be deterministic or LLM-based depending on ambiguity.

### Pipeline
Ordered stages A → B → C where later stages depend on earlier output.

Use when stage order is inherent.

### Map-Reduce
Apply the same analysis/transformation to many items, then reduce results into an aggregate.

### Discover → Act
First discover scope/work items, then construct the execution plan from what was found.

Use when workload cannot be known upfront.

### Planner → Executor
Planning component decomposes the goal; executor(s) perform work; planner may reassess.

Use for uncertain complex work, but avoid unnecessary planner layers for straightforward tasks.

### Supervisor → Workers
Supervisor dynamically assigns bounded work to workers and integrates results.

Use when central reasoning must remain adaptive.

### Generator → Verifier
One component creates findings/output; an independent component verifies them before acceptance.

Use when false positives/quality risk justify extra cost.

### Parallel Perspectives
Multiple agents analyse the same problem from different lenses, then synthesis weighs them.

Use for architecture, security, planning, or competing hypotheses.

### Sequential Handoff
Specialist A completes its domain work and passes a bounded artefact to B.

Use when domain stages genuinely differ. Flag waterfall-like micro-agent proliferation.

### Iterative Refinement
Generate → evaluate → improve → repeat until quality/termination criteria are met.

Must have explicit termination/no-progress criteria.

### Retry / Repair Loop
Execute → detect failure → diagnose/repair → retry.

Use for builds, tests, migrations, validation.

### Scatter → Verify → Gather
Fan out primary work, independently verify findings, then aggregate only supported results.

Strong Dynamic Workflow candidate for large audits/research.

### Conditional Branching
Evaluate condition/result and choose one of several paths.

Use deterministic branching where conditions are objective; LLM classification only where judgement is necessary.

### Hierarchical Decomposition
Large goal decomposes into subgoals, potentially recursively.

Use cautiously. Flag uncontrolled delegation depth and duplicated context.

### Human-in-the-loop
Execution pauses for explicit human review/approval before sensitive or irreversible continuation.

## Dynamic Workflow decision

Prefer Dynamic Workflow when:

- orchestration itself should be saved/rerun
- many agents are required
- fan-out/fan-in is large
- script variables should hold intermediate results
- loops/branching should be codified
- repeatable verification patterns are valuable
- migration/audit/research scale exceeds comfortable turn-by-turn coordination

Prefer Skill/Subagent orchestration when:

- only a few delegated tasks are needed
- Claude should adapt the plan turn-by-turn
- intermediate results are useful in the active reasoning context
- orchestration is not worth codifying

Prefer Agent Team when a handful of long-running peers need shared-task collaboration or peer messaging, not merely independent fan-out.

## Required workflow output

For each major workflow report:

- Control model: STATIC / DYNAMIC / HYBRID
- Pattern(s)
- Who holds the plan
- Current primitive
- Recommended primitive/composition
- Scale/concurrency assumptions
- State location
- Failure handling
- Termination criteria
- Verification strategy
