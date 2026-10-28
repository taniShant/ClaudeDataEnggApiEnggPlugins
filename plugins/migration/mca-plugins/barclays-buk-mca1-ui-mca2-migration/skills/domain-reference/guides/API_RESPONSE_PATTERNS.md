# API Response Patterns for MCA2

Master patterns for handling API responses, errors, and data validation.

Last Updated: March 25, 2026

---

## Table of Contents
1. [Standard Response Structure](#standard-response-structure)
2. [Response Validation](#response-validation)
3. [Error Handling](#error-handling)
4. [Pagination Patterns](#pagination-patterns)
5. [Request/Response Interceptors](#requestresponse-interceptors)
6. [Retry Logic](#retry-logic)
7. [Timeout Handling](#timeout-handling)
8. [Testing API Integration](#testing-api-integration)

---

## Standard Response Structure

### MCA2 API Response Format

```typescript
// src/types/api.ts
/**
 * Standard MCA2 API Response Structure
 */
export interface ApiResponse<T = any> {
  // Success flag
  success: boolean;

  // HTTP status code
  status: number;

  // Response data (can be array, object, or single value)
  data: T;

  // Error information (if any)
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };

  // Metadata (pagination, etc.)
  metadata?: {
    totalCount?: number;
    page?: number;
    pageSize?: number;
    totalPages?: number;
  };

  // Request tracking
  requestId?: string;
  timestamp?: string;
}

// Typed responses
export type RolesResponse = ApiResponse<Role[]>;
export type RoleDetailResponse = ApiResponse<Role>;
export type CreateRoleResponse = ApiResponse<Role>;
```

### Service Layer Response Handling

```typescript
// src/api/services.ts
export const createRolesServices = (api: ApiMCA) => ({
  /**
   * Fetch all roles with defensive response validation
   */
  fetchAll: async (params?: FetchAllRolesRequest): Promise<Role[]> => {
    const response = await api.service.call('fetchAllRoles', params);

    // Validate response structure
    if (!response) {
      throw new Error('No response from server');
    }

    // Validate data field exists
    if (!response.hasOwnProperty('data')) {
      throw new Error('Invalid response structure: missing data field');
    }

    // Ensure data is array
    const data = response.data;
    if (!Array.isArray(data)) {
      console.warn('API returned non-array for fetchAllRoles:', data);
      return [];
    }

    // Validate array items
    return data.map((item, index) => {
      if (!item.id || !item.name) {
        console.warn(`Role at index ${index} missing required fields:`, item);
        return {
          id: item.id || `unknown-${index}`,
          name: item.name || 'Unknown',
          ...item,
        };
      }
      return item;
    });
  },

  /**
   * Fetch single role with validation
   */
  fetchById: async (roleId: string): Promise<Role> => {
    if (!roleId) {
      throw new Error('roleId is required');
    }

    const response = await api.service.call('fetchRoleById', { roleId });

    // Validate response
    if (!response?.data) {
      throw new Error(`Role ${roleId} not found`);
    }

    const role = response.data;

    // Validate required fields
    if (!role.id || !role.name) {
      throw new Error('Role response missing required fields');
    }

    return role;
  },
});
```

---

## Response Validation

### Comprehensive Validation Schema

```typescript
// src/api/validation.ts
import * as yup from 'yup';

/**
 * Validate API response structure
 */
export const validateApiResponse = <T>(
  response: any,
  schema: yup.Schema<T>
): T => {
  try {
    // Validate response structure
    if (!response) {
      throw new Error('Empty response from server');
    }

    // Type validation
    if (typeof response !== 'object') {
      throw new Error('Response must be an object');
    }

    // Schema validation
    const validatedData = schema.validateSync(response);
    return validatedData;
  } catch (error) {
    if (error instanceof yup.ValidationError) {
      throw new Error(`Response validation failed: ${error.message}`);
    }
    throw error;
  }
};

/**
 * Role response validation schema
 */
export const roleResponseSchema = yup.object().shape({
  id: yup.string().required('Role ID is required'),
  name: yup.string().required('Role name is required'),
  description: yup.string().nullable(),
  businessUnitId: yup.string().required(),
  type: yup.string().oneOf(['admin', 'user', 'viewer']),
  isActive: yup.boolean().default(true),
  createdAt: yup.date().nullable(),
  updatedAt: yup.date().nullable(),
});

export const rolesListResponseSchema = yup.array().of(roleResponseSchema);

// Usage in service
fetchAll: async (): Promise<Role[]> => {
  const response = await api.service.call('fetchAllRoles');
  return validateApiResponse(response.data, rolesListResponseSchema);
}
```

---

## Error Handling

### Comprehensive Error Handler

```typescript
// src/api/errorHandler.ts
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  statusCode: number;
}

/**
 * Parse and handle API errors
 */
export const handleApiError = (error: any): ApiError => {
  // Network error
  if (!error.response) {
    return {
      code: 'NETWORK_ERROR',
      message: 'Network connection failed. Please check your internet connection.',
      statusCode: 0,
    };
  }

  const { status, data } = error.response;

  // Authentication error
  if (status === 401) {
    return {
      code: 'UNAUTHORIZED',
      message: 'Session expired. Please log in again.',
      statusCode: 401,
    };
  }

  // Authorization error
  if (status === 403) {
    return {
      code: 'FORBIDDEN',
      message: 'You do not have permission to perform this action.',
      statusCode: 403,
    };
  }

  // Not found
  if (status === 404) {
    return {
      code: 'NOT_FOUND',
      message: 'The requested resource was not found.',
      statusCode: 404,
    };
  }

  // Validation error
  if (status === 400) {
    return {
      code: 'VALIDATION_ERROR',
      message: data?.message || 'Request validation failed.',
      details: data?.details,
      statusCode: 400,
    };
  }

  // Conflict (duplicate, etc)
  if (status === 409) {
    return {
      code: 'CONFLICT',
      message: data?.message || 'Resource already exists.',
      statusCode: 409,
    };
  }

  // Server error
  if (status >= 500) {
    return {
      code: 'SERVER_ERROR',
      message: 'Server error. Please try again later.',
      statusCode: status,
    };
  }

  // Unknown error
  return {
    code: 'UNKNOWN_ERROR',
    message: data?.message || 'An unexpected error occurred.',
    statusCode: status,
  };
};

// Usage in Redux thunk
export const fetchRoles = createAsyncThunk(
  'roles/fetchRoles',
  async (_, { rejectWithValue }) => {
    try {
      return await api.roles.fetchAll();
    } catch (error) {
      const apiError = handleApiError(error);
      return rejectWithValue(apiError);
    }
  }
);
```

---

## Pagination Patterns

### Handling Paginated Responses

```typescript
// src/types/api.ts
export interface PaginatedResponse<T> {
  items: T[];
  totalCount: number;
  pageNumber: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

export interface PaginationParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// src/api/services.ts
export const createRolesServices = (api: ApiMCA) => ({
  /**
   * Fetch paginated roles
   */
  fetchPaginated: async (params: PaginationParams): Promise<PaginatedResponse<Role>> => {
    const response = await api.service.call('fetchRolesPaginated', params);

    // Validate response structure
    if (!response?.data) {
      throw new Error('Invalid pagination response');
    }

    const { items, totalCount, pageNumber, pageSize, totalPages } = response.data;

    // Validate pagination data
    if (!Array.isArray(items)) {
      throw new Error('Items must be an array');
    }

    return {
      items: items || [],
      totalCount: totalCount || 0,
      pageNumber: pageNumber || 1,
      pageSize: pageSize || 10,
      totalPages: totalPages || 1,
      hasNextPage: (pageNumber || 1) < (totalPages || 1),
      hasPreviousPage: (pageNumber || 1) > 1,
    };
  },
});

// src/store/slices/rolesSlice.ts
interface RolesState {
  items: Role[];
  pagination: {
    currentPage: number;
    pageSize: number;
    totalCount: number;
    totalPages: number;
  };
  loading: boolean;
  error: string | null;
}

const initialState: RolesState = {
  items: [],
  pagination: {
    currentPage: 1,
    pageSize: 10,
    totalCount: 0,
    totalPages: 0,
  },
  loading: false,
  error: null,
};

export const fetchRolesPaginated = createAsyncThunk<
  PaginatedResponse<Role>,
  PaginationParams
>(
  'roles/fetchPaginated',
  async (params, { rejectWithValue }) => {
    try {
      return await api.roles.fetchPaginated(params);
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch roles'
      );
    }
  }
);

// Reducer
.addCase(fetchRolesPaginated.fulfilled, (state, action) => {
  state.items = action.payload.items;
  state.pagination = {
    currentPage: action.payload.pageNumber,
    pageSize: action.payload.pageSize,
    totalCount: action.payload.totalCount,
    totalPages: action.payload.totalPages,
  };
  state.loading = false;
})
```

---

## Request/Response Interceptors

### Interceptor Setup

```typescript
// src/api/interceptors.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

export const setupInterceptors = (axiosInstance: AxiosInstance) => {
  /**
   * Request interceptor - add auth headers, logging
   */
  axiosInstance.interceptors.request.use(
    (config) => {
      // Add authorization header
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Add request ID for tracking
      config.headers['X-Request-Id'] = generateRequestId();

      // Log request
      console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  /**
   * Response interceptor - handle common errors, logging
   */
  axiosInstance.interceptors.response.use(
    (response) => {
      // Log response
      console.debug(`[API] Response: ${response.status}`, response.data);

      // Validate response has expected structure
      if (response.data === null || response.data === undefined) {
        console.warn('[API] Empty response received');
      }

      return response;
    },
    (error: AxiosError) => {
      // Handle 401 - redirect to login
      if (error.response?.status === 401) {
        console.warn('[API] Unauthorized - redirecting to login');
        // localStorage.clear();
        // window.location.href = '/login';
      }

      // Log error
      console.error('[API] Error:', {
        status: error.response?.status,
        message: error.message,
        data: error.response?.data,
      });

      return Promise.reject(error);
    }
  );
};
```

---

## Retry Logic

### Automatic Request Retry

```typescript
// src/api/retry.ts
export interface RetryConfig {
  maxRetries: number;
  initialDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  retryableStatusCodes: number[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
};

/**
 * Retry async operation with exponential backoff
 */
export const retryAsync = async <T>(
  operation: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> => {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: any;
  let delay = finalConfig.initialDelay;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      // Check if error is retryable
      const statusCode = error.response?.status;
      if (!finalConfig.retryableStatusCodes.includes(statusCode)) {
        throw error; // Not retryable, throw immediately
      }

      // Check if we've exhausted retries
      if (attempt === finalConfig.maxRetries) {
        break; // Exit loop, throw error below
      }

      // Wait before retrying
      console.warn(
        `[API] Retrying operation (attempt ${attempt + 1}/${finalConfig.maxRetries}) ` +
        `after ${delay}ms`
      );

      await new Promise(resolve => setTimeout(resolve, delay));

      // Increase delay for next retry
      delay = Math.min(
        delay * finalConfig.backoffMultiplier,
        finalConfig.maxDelay
      );
    }
  }

  throw lastError;
};

// Usage in API service
fetchAll: async (): Promise<Role[]> => {
  return retryAsync(
    () => api.service.call('fetchAllRoles'),
    { maxRetries: 3 }
  );
}
```

---

## Timeout Handling

### Request Timeouts

```typescript
// src/api/client.ts
import axios from 'axios';

export const createApiClient = () => {
  const client = axios.create({
    baseURL: process.env.REACT_APP_API_URL,
    timeout: 30000, // 30 second timeout
  });

  // Custom timeout per request
  return {
    get: <T>(url: string, timeout = 30000) =>
      client.get<T>(url, { timeout }),

    post: <T>(url: string, data: any, timeout = 30000) =>
      client.post<T>(url, data, { timeout }),

    put: <T>(url: string, data: any, timeout = 30000) =>
      client.put<T>(url, data, { timeout }),

    delete: <T>(url: string, timeout = 30000) =>
      client.delete<T>(url, { timeout }),
  };
};

// Handle timeout errors
try {
  await api.roles.fetchAll();
} catch (error) {
  if (error.code === 'ECONNABORTED') {
    showErrorMessage('Request timed out. Please try again.');
  } else {
    showErrorMessage(error.message);
  }
}
```

---

## Testing API Integration

### Mocking API Responses

```typescript
// src/api/__mocks__/services.ts
import { Role } from '../../types';

export const mockRoles: Role[] = [
  {
    id: '1',
    name: 'Admin',
    description: 'Administrator role',
    businessUnitId: 'bu1',
    type: 'admin',
    isActive: true,
  },
  {
    id: '2',
    name: 'User',
    description: 'Regular user role',
    businessUnitId: 'bu1',
    type: 'user',
    isActive: true,
  },
];

jest.mock('../../api/endpoints', () => ({
  api: {
    roles: {
      fetchAll: jest.fn().mockResolvedValue(mockRoles),
      fetchById: jest.fn().mockResolvedValue(mockRoles[0]),
      create: jest.fn().mockResolvedValue(mockRoles[0]),
    },
  },
}));
```

### Testing Redux Thunks with Mock API

```typescript
// src/store/slices/__tests__/rolesSlice.test.ts
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { fetchRoles } from '../rolesSlice';
import { mockRoles } from '../../../api/__mocks__/services';

const middleware = [thunk];
const mockStore = configureMockStore(middleware);

describe('fetchRoles thunk', () => {
  it('should dispatch fulfilled with role data', async () => {
    const store = mockStore({
      roles: { items: [], loading: false, error: null },
    });

    await store.dispatch(fetchRoles());

    const actions = store.getActions();
    expect(actions[0].type).toBe(fetchRoles.pending.type);
    expect(actions[1].type).toBe(fetchRoles.fulfilled.type);
    expect(actions[1].payload).toEqual(mockRoles);
  });

  it('should handle API errors', async () => {
    const error = new Error('API Error');
    jest.spyOn(api.roles, 'fetchAll').mockRejectedValue(error);

    const store = mockStore({
      roles: { items: [], loading: false, error: null },
    });

    await store.dispatch(fetchRoles());

    const actions = store.getActions();
    expect(actions[1].type).toBe(fetchRoles.rejected.type);
  });
});
```

---

## Summary Checklist

- ✅ Validate API response structure
- ✅ Ensure array methods return arrays
- ✅ Handle all error types (401, 403, 404, 500, etc.)
- ✅ Support pagination with metadata
- ✅ Add request/response interceptors
- ✅ Implement retry logic with exponential backoff
- ✅ Handle request timeouts gracefully
- ✅ Mock API responses for testing
- ✅ Log API calls for debugging
- ✅ Type API responses with TypeScript

---

## References
- Axios: https://axios-http.com
- Redux Toolkit: https://redux-toolkit.js.org
- Yup Validation: https://github.com/jquense/yup
- Mistake 23: API Response Structure Not Validated
