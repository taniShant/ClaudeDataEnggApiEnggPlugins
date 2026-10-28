# Required Plugin Validation Report

## 1. Executive Verdict

- Overall architecture rating: X/10
- Primary conclusion
- Highest-risk architectural issue
- Most valuable change

## 2. Current Architecture

Show the actual component tree and one-line responsibility for each component.

## 3. Primitive Placement Matrix

| Responsibility | Current home | Recommended home | Verdict | Evidence | Reason | Priority |
|---|---|---|---|---|---|---|

## 4. Agent Quality Audit

For each agent assess:

- role clarity
- responsibility boundary
- reasoning principles
- decision criteria
- trade-offs
- evidence grounding
- uncertainty handling
- verification
- collaboration/delegation
- tool boundary
- genericity

## 5. Skill Quality Audit

For each skill assess:

- trigger/discoverability
- bounded purpose
- reusable methodology
- principles/decision framework
- progressive disclosure
- references/scripts usage
- genericity
- verification
- duplication

## 6. Generality & Hardcoding Audit

| Value/rule | Location | Classification | Valid? | Recommended action | Severity |
|---|---|---|---|---|---|

Explicitly identify examples accidentally promoted to generic rules.

## 7. Policy / Knowledge Scope

Classify important instructions as:

- generic principle
- domain knowledge
- organisation policy
- team convention
- project constraint
- runtime configuration
- example

Flag scope mismatches.

## 8. Workflow Architecture

For every major workflow:

- STATIC / DYNAMIC / HYBRID
- pattern(s)
- who holds the plan
- current implementation
- recommended implementation
- state location
- scale
- failure handling
- termination
- verification

## 9. Dynamic Workflow Assessment

Explicitly state which orchestration should/should not become a Dynamic Workflow and why.

## 10. Enforcement Assessment

Identify:

- advisory rules correctly left to Claude
- invariants incorrectly left as prompts
- hooks/scripts that should enforce deterministic behaviour
- hooks incorrectly performing reasoning-heavy work

## 11. Context & Progressive Disclosure

Rate HIGH / MEDIUM / LOW issues involving:

- always-loaded content
- oversized Skills
- unnecessary references in core context
- duplicated context
- missing isolation
- unnecessary isolation

## 12. Over-Engineering

List abstractions/components that should be simplified, merged, or removed.

## 13. Under-Engineering

List responsibilities that need proper extraction, isolation, deterministic implementation, enforcement, or workflow codification.

## 14. Target Architecture

Show the complete recommended plugin tree and runtime composition.

## 15. Refactoring Map

For each change:

CURRENT: `path/component`
→ TARGET: `path/component`

- Move/change:
- Keep:
- Why:
- Context impact: High/Medium/Low
- Behavioural risk: High/Medium/Low
- Priority: P0/P1/P2

## 16. KEEP / DO NOT EXTRACT

Mandatory. Identify components/logic already correctly placed, including agent logic that should deliberately remain inline.

## 17. Priority

### P0 — correctness/security/reliability
### P1 — architectural quality
### P2 — context/maintainability optimisation

## 18. Scores

| Dimension | Score |
|---|---:|
| Overall | X/10 |
| Primitive placement | X/10 |
| Agent quality | X/10 |
| Skill quality | X/10 |
| Generality/portability | X/10 |
| Policy scoping | X/10 |
| Workflow/orchestration | X/10 |
| Dynamic workflow usage | X/10 |
| Enforcement | X/10 |
| Context efficiency | X/10 |
| Maintainability | X/10 |

## 19. Top Findings

Top 5 findings ranked by architectural impact.
