---
name: block-secret-output
trigger: pre-write
applies_to: [Write, Edit]
description: Deterministic hook that prevents secrets, credentials or tokens from being written to output files.
---

## Purpose

Prevents credentials, tokens, connection strings with passwords, API keys and other secrets from being persisted in generated files. This hook applies to all Write and Edit tool calls regardless of file type or destination.

## Detection Patterns

The following patterns are matched against file content before any write is committed:

| Pattern Type | Description |
|---|---|
| AWS Access Key | Strings beginning with `AKIA` followed by 16 uppercase alphanumeric characters |
| Bearer Token | Strings matching `Bearer [A-Za-z0-9\-._~+/]+=*` with sufficient entropy |
| Password in Connection String | Substrings matching `password=`, `pwd=`, `passwd=` followed by a non-empty value |
| Personal Access Token | Strings matching known PAT formats (GitHub, Azure DevOps, GitLab prefixes) |
| Private Key Block | Content containing `-----BEGIN RSA PRIVATE KEY-----`, `-----BEGIN PRIVATE KEY-----`, or `-----BEGIN EC PRIVATE KEY-----` |
| Base64 Credentials | Base64-encoded strings matching known credential prefixes after decoding |
| Generic High-Entropy Secret | Strings matching patterns used for API keys, client secrets, and symmetric keys with entropy threshold |

Detection is applied to the full proposed file content, including multiline strings and embedded configuration blocks.

## Behaviour

If a secret pattern is detected in a proposed Write or Edit operation:

1. **BLOCK** the write. Do not persist the file.
2. Return a `BLOCKED_SAFETY` status containing:
   - `pattern_type`: the category of secret detected (e.g. `AWS_ACCESS_KEY`, `PASSWORD_IN_CONNECTION_STRING`). **Never include the actual secret value.**
   - `file_path`: the path where the write was attempted
   - `suggested_alternative`: one or more of the following as appropriate:
     - Use a secret store reference (e.g. `{{ secret('my-secret-name') }}`)
     - Use an environment variable reference (e.g. `os.environ['MY_SECRET']`)
     - Use a vault path reference (e.g. `vault://barclays/data-eng/my-credential`)

## Never Log Secret Values

The block message must never include the actual secret value. Only the pattern type, approximate location (line range), and file path are included in the block response. This applies to logs, result manifests, and any downstream output.

## Deterministic Operation

This hook operates deterministically before any file write is committed. It cannot be bypassed by model reasoning or prompt instructions. Detection logic is maintained externally to the prompt context.
