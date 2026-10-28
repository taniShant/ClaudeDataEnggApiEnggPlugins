# Expert Agent and Skill Quality

Technical structure alone does not make an expert component good.

## Governing principle

Expert components should encode how to reason, not what answer to produce.

## Agent quality audit

Validate:

### Role clarity
Clear domain/persona and outcome ownership.

### Responsibility boundaries
The agent knows what it owns and what it should delegate or leave to another capability.

### Durable reasoning principles
Principles survive changes in repository, technology version, or one specific implementation.

### Decision criteria
The agent knows what forces determine a choice.

### Trade-off reasoning
It evaluates competing concerns rather than prescribing a default without justification.

### Evidence grounding
Recommendations must trace to requirements, code, configuration, runtime evidence, or explicit policy.

### Uncertainty handling
The agent distinguishes known facts, assumptions, missing evidence, and hypotheses.

### Simplicity
Prefer minimum sufficient complexity. Do not introduce architecture because it is fashionable or technically possible.

### Verification
The agent checks that conclusions satisfy the original constraints and acceptance criteria.

### Collaboration
Clear conditions for when another domain/expert/context is needed.

### Genericity
Project-specific conclusions must not masquerade as universal expert principles.

### Tool boundaries
The agent has only the capabilities it needs; connectivity and deterministic work are not duplicated in prose.

### Delegation ownership
Do not create uncontrolled recursive agent topology when orchestration should own delegation.

## Skill quality audit

Validate:

- clear trigger/use conditions
- bounded purpose
- reusable methodology
- durable principles
- decision framework
- explicit inputs/outputs where useful
- trade-offs and exceptions
- progressive disclosure
- references for detailed/version-specific material
- scripts for deterministic operations
- verification step
- portability/genericity
- no unnecessary persona or isolated-worker behaviour

## Weak expert component indicators

Flag components dominated by:

- "always use X" without scope/evidence
- vendor/product prescriptions presented as principles
- copied project decisions
- long checklists with no decision model
- examples promoted to rules
- unexplained numeric thresholds
- one happy-path procedure with no failure/exception handling
- generic expert claims without repository evidence

## Strong expert component pattern

Principles → decision criteria → evidence → alternatives → trade-offs → decision → verification.
