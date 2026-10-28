# domain

BUK banking product domain plugins — cross-cutting capabilities specific to Barclays UK product domains such as payments, mortgages, onboarding, current accounts, and savings.

These plugins encode domain knowledge and workflows and are scoped to a specific BUK product line rather than a technology stack.

## Available plugins

| Plugin | Status | Description |
|---|---|---|
| [barclays-buk-data-product-builder](barclays-buk-data-product-builder/) | 🚧 Draft | Data modelling, source-to-target mapping, PySpark pipeline generation (Glue/Databricks), and data validation SQL generation from Excel mappings |

## Adding a domain plugin

Follow the naming convention: `barclays-buk-<product-domain>-<capability>`
