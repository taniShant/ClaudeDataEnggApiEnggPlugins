# Form Validation Patterns for MCA2

Master patterns for form handling and validation using Yup + Formik/React Hook Form.

Last Updated: March 25, 2026

---

## Table of Contents
1. [Yup Schema Basics](#yup-schema-basics)
2. [Formik Integration](#formik-integration)
3. [React Hook Form Integration](#react-hook-form-integration)
4. [Custom Validation Rules](#custom-validation-rules)
5. [Async Validation](#async-validation)
6. [Dynamic Fields](#dynamic-fields)
7. [Error Display](#error-display)
8. [Testing Forms](#testing-forms)

---

## Yup Schema Basics

### Standard Form Schema

```typescript
// src/validation/roleSchema.ts
import * as yup from 'yup';

export const createRoleSchema = yup.object().shape({
  name: yup
    .string()
    .required('Role name is required')
    .min(3, 'Role name must be at least 3 characters')
    .max(50, 'Role name must not exceed 50 characters')
    .matches(
      /^[a-zA-Z0-9_-]+$/,
      'Role name can only contain letters, numbers, hyphens, and underscores'
    ),

  description: yup
    .string()
    .max(500, 'Description must not exceed 500 characters'),

  businessUnitId: yup
    .string()
    .required('Business unit is required'),

  type: yup
    .string()
    .oneOf(['admin', 'user', 'viewer'], 'Invalid role type')
    .required('Role type is required'),

  isActive: yup.boolean().default(true),

  expiryDate: yup
    .date()
    .nullable()
    .typeError('Expiry date must be a valid date')
    .min(new Date(), 'Expiry date must be in the future'),
});

export type CreateRoleFormData = yup.InferType<typeof createRoleSchema>;
```

### Common Validation Rules

```typescript
// Email validation
email: yup
  .string()
  .email('Invalid email address')
  .required('Email is required'),

// Phone validation
phone: yup
  .string()
  .matches(/^\+?[1-9]\d{1,14}$/, 'Invalid phone number format'),

// URL validation
website: yup
  .string()
  .url('Invalid URL format'),

// Enum validation
status: yup
  .string()
  .oneOf(['active', 'inactive', 'pending'])
  .required('Status is required'),

// Numeric validation
userCount: yup
  .number()
  .required('User count is required')
  .positive('User count must be positive')
  .integer('User count must be a whole number'),

// Array validation
tags: yup
  .array()
  .of(yup.string())
  .min(1, 'At least one tag is required')
  .max(10, 'Maximum 10 tags allowed'),

// Conditional validation
confirmPassword: yup
  .string()
  .oneOf([yup.ref('password')], 'Passwords must match')
  .required('Confirm password is required'),
```

---

## Formik Integration

### Complete Formik Form Component

```typescript
import { Formik, Form, FormikHelpers } from 'formik';
import { FormItem, FormInput, FormSelect, Button } from '@barclays/blueprint-react';
import { createRoleSchema, CreateRoleFormData } from '../validation/roleSchema';

interface CreateRoleFormProps {
  onSubmit: (data: CreateRoleFormData) => Promise<void>;
  isLoading?: boolean;
}

export const CreateRoleForm: React.FC<CreateRoleFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const initialValues: CreateRoleFormData = {
    name: '',
    description: '',
    businessUnitId: '',
    type: 'user',
    isActive: true,
    expiryDate: null,
  };

  const handleSubmit = async (
    values: CreateRoleFormData,
    { setSubmitting, setErrors }: FormikHelpers<CreateRoleFormData>
  ) => {
    try {
      await onSubmit(values);
      // Success - handled by parent component
    } catch (error) {
      // Set field-level errors if available
      if (error instanceof Error && error.message.includes('name')) {
        setErrors({ name: 'This role name already exists' });
      } else {
        setErrors({ submit: 'Failed to create role' });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Formik
      initialValues={initialValues}
      validationSchema={createRoleSchema}
      onSubmit={handleSubmit}
      validateOnChange={true}
      validateOnBlur={true}
    >
      {({ values, errors, touched, isSubmitting, isValid }) => (
        <Form>
          {/* Name Field */}
          <FormItem
            label="Role Name"
            error={touched.name ? errors.name : undefined}
            required
            render={(props) => (
              <FormInput
                {...props}
                type="text"
                name="name"
                value={values.name}
                disabled={isSubmitting || isLoading}
              />
            )}
          />

          {/* Description Field */}
          <FormItem
            label="Description"
            error={touched.description ? errors.description : undefined}
            render={(props) => (
              <textarea
                {...props}
                name="description"
                value={values.description}
                disabled={isSubmitting || isLoading}
              />
            )}
          />

          {/* Business Unit Select */}
          <FormItem
            label="Business Unit"
            error={touched.businessUnitId ? errors.businessUnitId : undefined}
            required
            render={(props) => (
              <FormSelect {...props} name="businessUnitId">
                <option value="">Select a business unit</option>
                <option value="bu1">Business Unit 1</option>
                <option value="bu2">Business Unit 2</option>
              </FormSelect>
            )}
          />

          {/* Submit Button */}
          <Button
            type="submit"
            variant="primary"
            disabled={!isValid || isSubmitting || isLoading}
          >
            {isSubmitting ? 'Creating...' : 'Create Role'}
          </Button>
        </Form>
      )}
    </Formik>
  );
};
```

---

## React Hook Form Integration

### Modern Form Handling with React Hook Form

```typescript
import { useForm, Controller, SubmitHandler } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { FormItem, FormInput, FormSelect, Button } from '@barclays/blueprint-react';
import { createRoleSchema, CreateRoleFormData } from '../validation/roleSchema';

interface CreateRoleFormProps {
  onSubmit: (data: CreateRoleFormData) => Promise<void>;
  isLoading?: boolean;
}

export const CreateRoleForm: React.FC<CreateRoleFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<CreateRoleFormData>({
    resolver: yupResolver(createRoleSchema),
    mode: 'onChange',
  });

  const onSubmitHandler: SubmitHandler<CreateRoleFormData> = async (data) => {
    try {
      await onSubmit(data);
    } catch (error) {
      console.error('Form submission error:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmitHandler)}>
      {/* Name Field */}
      <Controller
        name="name"
        control={control}
        render={({ field }) => (
          <FormItem
            label="Role Name"
            error={errors.name?.message}
            required
            render={(props) => (
              <FormInput
                {...props}
                {...field}
                type="text"
                disabled={isSubmitting || isLoading}
              />
            )}
          />
        )}
      />

      {/* Description Field */}
      <Controller
        name="description"
        control={control}
        render={({ field }) => (
          <FormItem
            label="Description"
            error={errors.description?.message}
            render={(props) => (
              <textarea
                {...props}
                {...field}
                disabled={isSubmitting || isLoading}
              />
            )}
          />
        )}
      />

      {/* Business Unit Select */}
      <Controller
        name="businessUnitId"
        control={control}
        render={({ field }) => (
          <FormItem
            label="Business Unit"
            error={errors.businessUnitId?.message}
            required
            render={(props) => (
              <FormSelect
                {...props}
                {...field}
                disabled={isSubmitting || isLoading}
              >
                <option value="">Select a business unit</option>
                <option value="bu1">Business Unit 1</option>
                <option value="bu2">Business Unit 2</option>
              </FormSelect>
            )}
          />
        )}
      />

      {/* Submit Button */}
      <Button
        type="submit"
        variant="primary"
        disabled={!isValid || isSubmitting || isLoading}
      >
        {isSubmitting ? 'Creating...' : 'Create Role'}
      </Button>
    </form>
  );
};
```

---

## Custom Validation Rules

### Reusable Custom Validators

```typescript
// src/validation/customValidators.ts
import * as yup from 'yup';

// Username uniqueness check
export const uniqueUsername = yup
  .string()
  .test('unique-username', 'This username is already taken', async (value) => {
    if (!value) return true;

    try {
      const exists = await api.users.checkUsernameExists(value);
      return !exists;
    } catch {
      return true; // Don't block on error
    }
  });

// Email uniqueness check
export const uniqueEmail = yup
  .string()
  .test('unique-email', 'This email is already registered', async (value) => {
    if (!value) return true;

    try {
      const exists = await api.users.checkEmailExists(value);
      return !exists;
    } catch {
      return true;
    }
  });

// Complex custom rule
export const validServiceConfiguration = yup.object().shape({
  serviceId: yup.string().required(),
  minInstances: yup.number().required().min(1),
  maxInstances: yup.number().required(),
}).test(
  'valid-instances',
  'Max instances must be greater than min instances',
  (config) => {
    if (!config) return true;
    return config.maxInstances > config.minInstances;
  }
);

// Usage in schema
export const createServiceSchema = yup.object().shape({
  username: uniqueUsername,
  email: uniqueEmail,
  config: validServiceConfiguration,
});
```

---

## Async Validation

### Handling Async Validators

```typescript
// Schema with async validation
export const createRoleSchema = yup.object().shape({
  name: yup
    .string()
    .required('Role name is required')
    .test('unique-name', 'This role name already exists', async (value) => {
      if (!value) return true;

      try {
        const exists = await api.roles.checkNameExists(value);
        return !exists;
      } catch (error) {
        console.error('Uniqueness check failed:', error);
        return true; // Don't block form on error
      }
    }),
});

// Component handling async validation
interface AsyncValidationFieldProps {
  label: string;
  name: string;
  validator: (value: string) => Promise<boolean>;
}

export const AsyncValidationField: React.FC<AsyncValidationFieldProps> = ({
  label,
  name,
  validator,
}) => {
  const [isChecking, setIsChecking] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (!value) {
      setValidationError(null);
      return;
    }

    setIsChecking(true);
    try {
      const isValid = await validator(value);
      setValidationError(isValid ? null : 'This value is already taken');
    } catch (error) {
      setValidationError('Validation check failed');
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <FormItem
      label={label}
      error={validationError || undefined}
      render={(props) => (
        <FormInput
          {...props}
          type="text"
          name={name}
          onBlur={handleBlur}
          disabled={isChecking}
        />
      )}
    />
  );
};
```

---

## Dynamic Fields

### Forms with Add/Remove Fields

```typescript
import { FieldArray, Formik, Form } from 'formik';

export const DynamicServicesForm: React.FC = () => {
  const initialValues = {
    services: [{ serviceId: '', accessLevel: 'read' }],
  };

  const validationSchema = yup.object().shape({
    services: yup.array().of(
      yup.object().shape({
        serviceId: yup.string().required('Service is required'),
        accessLevel: yup
          .string()
          .oneOf(['read', 'write', 'admin'])
          .required(),
      })
    ),
  });

  return (
    <Formik
      initialValues={initialValues}
      validationSchema={validationSchema}
      onSubmit={async (values) => {
        await api.roles.updateServices(values.services);
      }}
    >
      {({ values, errors, touched }) => (
        <Form>
          <FieldArray name="services">
            {(fieldArrayHelpers) => (
              <div>
                {values.services.map((_, index) => (
                  <div key={index}>
                    {/* Service ID Field */}
                    <FormItem
                      label={`Service ${index + 1}`}
                      error={
                        touched.services?.[index]?.serviceId
                          ? errors.services?.[index]?.serviceId
                          : undefined
                      }
                      render={(props) => (
                        <FormSelect
                          {...props}
                          name={`services.${index}.serviceId`}
                        >
                          <option value="">Select service</option>
                          <option value="svc1">Service 1</option>
                          <option value="svc2">Service 2</option>
                        </FormSelect>
                      )}
                    />

                    {/* Access Level */}
                    <FormItem
                      label="Access Level"
                      render={(props) => (
                        <FormSelect {...props} name={`services.${index}.accessLevel`}>
                          <option value="read">Read</option>
                          <option value="write">Write</option>
                          <option value="admin">Admin</option>
                        </FormSelect>
                      )}
                    />

                    {/* Remove Button */}
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => fieldArrayHelpers.remove(index)}
                    >
                      Remove
                    </Button>
                  </div>
                ))}

                {/* Add Button */}
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    fieldArrayHelpers.push({
                      serviceId: '',
                      accessLevel: 'read',
                    })
                  }
                >
                  Add Service
                </Button>
              </div>
            )}
          </FieldArray>

          <Button type="submit" variant="primary">
            Save
          </Button>
        </Form>
      )}
    </Formik>
  );
};
```

---

## Error Display

### Comprehensive Error Handling

```typescript
// src/components/FormErrorDisplay.tsx
interface FormErrorDisplayProps {
  fieldError?: string;
  formError?: string;
  isValidating?: boolean;
}

export const FormErrorDisplay: React.FC<FormErrorDisplayProps> = ({
  fieldError,
  formError,
  isValidating,
}) => {
  if (isValidating) {
    return <Type element="span" size="sm">Validating...</Type>;
  }

  if (fieldError) {
    return (
      <MessageAlert
        type="error"
        message={fieldError}
        isVisible={true}
      />
    );
  }

  if (formError) {
    return (
      <MessageAlert
        type="error"
        message={formError}
        isVisible={true}
      />
    );
  }

  return null;
};

// Usage in form
<FormItem
  label="Role Name"
  error={errors.name}
  render={(props) => (
    <FormInput
      {...props}
      {...field}
      type="text"
    />
  )}
/>

{/* Form-level error */}
{formError && (
  <MessageAlert
    type="error"
    title="Form Error"
    message={formError}
  />
)}
```

---

## Testing Forms

### Form Component Tests

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateRoleForm } from './CreateRoleForm';

describe('CreateRoleForm', () => {
  it('should render form fields', () => {
    render(<CreateRoleForm onSubmit={jest.fn()} />);

    expect(screen.getByLabelText('Role Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Business Unit')).toBeInTheDocument();
  });

  it('should show validation errors on blur', async () => {
    render(<CreateRoleForm onSubmit={jest.fn()} />);

    const input = screen.getByLabelText('Role Name') as HTMLInputElement;
    fireEvent.blur(input);

    await waitFor(() => {
      expect(screen.getByText('Role name is required')).toBeInTheDocument();
    });
  });

  it('should submit form with valid data', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<CreateRoleForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('Role Name'), 'admin');
    await user.selectOptions(
      screen.getByLabelText('Business Unit'),
      'bu1'
    );
    await user.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'admin',
          businessUnitId: 'bu1',
        })
      );
    });
  });

  it('should disable submit when form is invalid', async () => {
    render(<CreateRoleForm onSubmit={jest.fn()} />);

    const submitButton = screen.getByText('Create Role') as HTMLButtonElement;
    expect(submitButton).toBeDisabled();
  });
});
```

---

## Summary Checklist

- ✅ Use Yup for schema validation
- ✅ Define schemas in separate files
- ✅ Use Formik or React Hook Form for form state
- ✅ Show validation errors on blur/change
- ✅ Handle async validation properly
- ✅ Support dynamic form fields
- ✅ Show loading state during submission
- ✅ Handle and display submission errors
- ✅ Disable submit when form invalid
- ✅ Test form submission and validation

---

## References
- Yup Documentation: https://github.com/jquense/yup
- Formik Documentation: https://formik.org
- React Hook Form: https://react-hook-form.com
- Component Audit Checklist: COMPONENT_AUDIT_CHECKLIST.md
