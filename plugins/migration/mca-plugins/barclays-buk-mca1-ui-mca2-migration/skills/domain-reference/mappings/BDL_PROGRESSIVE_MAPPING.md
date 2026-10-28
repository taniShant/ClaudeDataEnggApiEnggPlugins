# BDL_PROGRESSIVE_MAPPING.md

## Overview

Maps `<mca-progressive>` and `<mca-progressiveitem>` (step-by-step wizard/stepper showing numbered steps with states) to Blueprint-React `ProgressVertical` + `ProgressVerticalItem`.

## MCA1 Pattern

```html
<mca-progressive id="wizardSteps">
  <mca-progressiveitem
    title="Personal Details"
    state="complete"
    id="step1"
  >
    Step 1 content here
  </mca-progressiveitem>
  <mca-progressiveitem
    title="Address"
    state="active"
    id="step2"
  >
    Step 2 content here
  </mca-progressiveitem>
  <mca-progressiveitem
    title="Confirmation"
    state="pending"
    id="step3"
  >
    Step 3 content here
  </mca-progressiveitem>
</mca-progressive>
```

### Attributes — `<mca-progressive>`

| Attribute | Description | Default |
|-----------|-------------|---------|
| `id` | Element ID | — |

### Attributes — `<mca-progressiveitem>`

| Attribute | Values | Description |
|-----------|--------|-------------|
| `title` | string | Step heading text |
| `state` | `complete`, `active`, `pending` | Visual state of the step |
| `id` | string | Element ID |

### JavaScript API

```javascript
var progressive = $('#wizardSteps').getComponent();

// Navigate to a specific step
progressive.goToStep(stepIndex);

// Get current active step
progressive.getCurrentStep();
```

---

## Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import {
  ProgressVertical,
  ProgressVerticalItem,
  Badge,
  Type,
  Icon,
  Section,
  SectionItem,
  Button,
  Arrange,
  ArrangeItem
} from '@barclays/blueprint-react';

interface Step {
  id: string;
  title: string;
  content: React.ReactNode;
}

interface WizardProps {
  steps: Step[];
}

export const StepWizard: React.FC<WizardProps> = ({ steps }) => {
  const [currentStep, setCurrentStep] = useState(0);

  const getStepState = (index: number): 'complete' | 'in-progress' | 'default' => {
    if (index < currentStep) return 'complete';
    if (index === currentStep) return 'in-progress';
    return 'default';
  };

  const getStepBadge = (index: number) => {
    const state = getStepState(index);
    if (state === 'complete') {
      return <Badge><Icon icon="tick" size="xs" /></Badge>;
    }
    return <Badge>{index + 1}</Badge>;
  };

  return (
    <Section>
      <SectionItem>
        <ProgressVertical>
          {steps.map((step, index) => (
            <ProgressVerticalItem
              key={step.id}
              state={getStepState(index)}
              badge={getStepBadge(index)}
              heading={<Type weight="medium">{step.title}</Type>}
            >
              {index === currentStep && (
                <>
                  {step.content}
                  <Arrange gap="fixed">
                    {currentStep > 0 && (
                      <ArrangeItem size="fit">
                        <Button variant="secondary" onClick={() => setCurrentStep(currentStep - 1)}>
                          Back
                        </Button>
                      </ArrangeItem>
                    )}
                    {currentStep < steps.length - 1 && (
                      <ArrangeItem size="fit">
                        <Button variant="primary" onClick={() => setCurrentStep(currentStep + 1)}>
                          Continue
                        </Button>
                      </ArrangeItem>
                    )}
                  </Arrange>
                </>
              )}
            </ProgressVerticalItem>
          ))}
        </ProgressVertical>
      </SectionItem>
    </Section>
  );
};
```

---

## Attribute Mapping

| MCA1 Attribute | Blueprint Prop | Notes |
|----------------|---------------|-------|
| `<mca-progressive>` | `<ProgressVertical>` | Container component |
| `<mca-progressiveitem>` | `<ProgressVerticalItem>` | Individual step |
| `title` | `heading` prop (ReactNode) | Wrap in `<Type weight="medium">` |
| `state="complete"` | `state="complete"` | Direct mapping |
| `state="active"` | `state="in-progress"` | Name differs: active → in-progress |
| `state="pending"` | `state="default"` | Name differs: pending → default |
| Content (children) | `children` of `ProgressVerticalItem` | Only render for active step |
| `id` | `key` prop (for React list) or `id` | Standard HTML attribute |

## API Mapping

| MCA1 jQuery API | React Equivalent | Notes |
|-----------------|-----------------|-------|
| `.goToStep(index)` | `setCurrentStep(index)` | useState setter |
| `.getCurrentStep()` | `currentStep` state value | Read from useState |

---

## Iron Rules

1. **`ProgressVerticalItem` requires a `badge` prop** — it is mandatory, always provide one
2. **State naming differs**: MCA1 `active` → Blueprint `in-progress`, MCA1 `pending` → Blueprint `default`
3. **Only show step content for the active step** — render children conditionally based on `currentStep`
4. **Badge shows step number for incomplete steps, tick icon for complete** — use `<Badge>` with number or `<Icon icon="tick">`
5. **Navigation buttons are NOT part of ProgressVertical** — add them inside the active step's content area
