---
name: cwe-078-os-command-injection
description: "CWE-78: OS Command Injection Remediation — Remediate OS command injection vulnerabilities by eliminating shell invocation with user-controlled input. This skill identifies where untrusted data "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-78: OS Command Injection Remediation
## Quick Start

This skill provides the fix pattern for CWE-078. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-078 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-78
- **CWE Name**: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
- **Severity**: Critical
- **OWASP Category**: A03:2021 - Injection

## Purpose

Remediate OS command injection vulnerabilities by eliminating shell invocation with user-controlled input. This skill identifies where untrusted data is passed to shell commands and applies the appropriate fix: replacing shell-based execution with direct process execution using argument lists, replacing dynamic commands with language-native libraries, or applying strict allowlist validation when shell execution is unavoidable. It covers Python (subprocess), Java (ProcessBuilder), and Node.js (child_process.execFile vs exec).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the command injection vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-78`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and command execution API.**
   - Examine import statements and the specific API being used:
     - Python: `os.system`, `os.popen`, `subprocess.call/run/Popen` with `shell=True`, `commands.getoutput`.
     - Java: `Runtime.getRuntime().exec(String)`, `ProcessBuilder` with shell invocation.
     - Node.js: `child_process.exec`, `child_process.execSync`, `shell: true` option.

3. **Identify the user-controlled input in the command.**
   - Trace the user-controlled data back to its source.
   - Determine how it is incorporated into the command string (concatenation, f-string, template literal, format string).

4. **Determine the best fix strategy.**
   - **Strategy 1 -- Replace with language-native library (preferred):** If the command performs a common operation (file copy, HTTP request, file listing, etc.), replace the shell command with a language-native equivalent (e.g., `shutil.copy` instead of `cp`, `fs.readdir` instead of `ls`).
   - **Strategy 2 -- Use argument list execution (no shell):** Replace `shell=True` execution with argument list execution that bypasses the shell entirely, preventing shell metacharacter interpretation.
   - **Strategy 3 -- Allowlist validation (last resort):** If the command must include user input and a shell is unavoidable (rare), validate the input against a strict allowlist of permitted values.

5. **Apply the fix.**
   - For Strategy 1: Replace the entire command execution block with the native library call.
   - For Strategy 2: Convert the command string into a list of arguments and remove `shell=True` (or equivalent).
   - For Strategy 3: Add allowlist validation before the command execution.

6. **Apply the edit.**
   - Use `Edit` to replace the vulnerable code with the safe version.
   - Add necessary imports (e.g., `import subprocess`, `import shutil`, `const { execFile } = require('child_process')`).
   - Preserve code formatting, indentation, and surrounding logic.

7. **Scan for similar patterns in the same file.**
   - Use `Grep` to find other instances of the same vulnerable pattern.
   - Apply the same fix to all instances.

8. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the fix is syntactically correct.
   - Confirm that no user input flows into a shell-interpreted command string.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the safe replacement>",
      "fix_type": "native_library_replacement | argument_list_execution | allowlist_validation"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "imports_removed": ["<string: any import statements that are no longer needed>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries have valid `fixed_code` with no shell invocation of user input.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

OS command injection occurs when user-controlled input is incorporated into a string that is executed as an operating system command through a shell interpreter. The shell interprets metacharacters (`;`, `|`, `&&`, `||`, `` ` ``, `$()`, etc.) in the input, allowing an attacker to execute arbitrary commands.

### Detection Patterns

**Python -- shell execution with user input:**
```
# os.system:               os.system("ping " + host)
# os.system f-string:      os.system(f"nslookup {domain}")
# os.popen:                os.popen("grep " + pattern + " file.txt")
# subprocess shell=True:   subprocess.call("ls " + directory, shell=True)
# subprocess shell=True:   subprocess.run(f"convert {input_file} {output_file}", shell=True)
# commands (Python 2):     commands.getoutput("cat " + filename)
```

**Java -- shell execution with user input:**
```
# Runtime.exec(String):    Runtime.getRuntime().exec("ping " + host)
#   Note: Runtime.exec(String) DOES parse the string, but does not use a shell.
#   However, Runtime.exec(String[]) with cmd/sh is a shell injection:
#   Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", "ping " + host})
# ProcessBuilder with sh:  new ProcessBuilder("/bin/sh", "-c", "ping " + host)
```

**Node.js -- shell execution with user input:**
```
# exec:                    exec('ping ' + host, callback)
# execSync:                execSync(`nslookup ${domain}`)
# spawn with shell:        spawn('ping ' + host, { shell: true })
```

**Indicators of user-controlled input:**
- Variables sourced from `request.args`, `request.form`, `req.query`, `req.params`, `req.body`, `getParameter()`, command-line arguments, environment variables.
- File names from upload operations.
- Data from databases or external APIs (if not validated).

## Fix Pattern

The primary fix is to avoid passing user input through a shell interpreter entirely. This is achieved by:

1. **Replacing shell commands with native library equivalents** (eliminates command execution entirely).
2. **Using argument list execution** (the OS executes the program directly without a shell to interpret metacharacters).
3. **Allowlist validation** (only permits known-safe values when shell execution is unavoidable).

**Why escaping/quoting is insufficient:**
- Shell escaping functions (e.g., `shlex.quote` in Python) can help but are error-prone and shell-specific.
- Different shells (bash, sh, cmd.exe, PowerShell) have different escaping rules.
- Argument list execution avoids the problem entirely by not invoking a shell.

## Language-Specific Examples

### Python -- subprocess with shell=True

**Before (vulnerable):**
```python
import subprocess

def ping_host(host):
    result = subprocess.run(f"ping -c 4 {host}", shell=True, capture_output=True, text=True)
    return result.stdout
```

**After (fixed):**
```python
import subprocess

def ping_host(host):
    result = subprocess.run(
        ["ping", "-c", "4", host],
        capture_output=True, text=True
    )
    return result.stdout
```

**Explanation:** `shell=True` is removed and the command string is replaced with a list of arguments. The OS executes `ping` directly with `host` as a literal argument. Even if `host` contains `;rm -rf /`, it is passed as a single argument to `ping`, not interpreted by a shell.

### Python -- os.system

**Before (vulnerable):**
```python
import os

def convert_image(input_path, output_path):
    os.system(f"convert {input_path} {output_path}")
```

**After (fixed -- native library):**
```python
from PIL import Image

def convert_image(input_path, output_path):
    img = Image.open(input_path)
    img.save(output_path)
```

**Explanation:** The shell command is replaced entirely with the Pillow (PIL) library, which handles image conversion natively in Python. This eliminates command execution and the entire class of injection risk. This is the preferred fix when a native library can accomplish the same task.

**After (fixed -- subprocess with list args, if native library is not available):**
```python
import subprocess

def convert_image(input_path, output_path):
    subprocess.run(
        ["convert", input_path, output_path],
        check=True
    )
```

**Explanation:** If a native library is not available, `os.system` is replaced with `subprocess.run` using a list of arguments (no `shell=True`). Each path is passed as a separate argument, not interpreted by a shell.

### Python -- Allowlist Validation (when dynamic command component is needed)

**Before (vulnerable):**
```python
import subprocess

def run_tool(tool_name, target):
    subprocess.run(f"{tool_name} {target}", shell=True)
```

**After (fixed):**
```python
import subprocess

ALLOWED_TOOLS = {
    "nmap": "/usr/bin/nmap",
    "ping": "/usr/bin/ping",
    "dig": "/usr/bin/dig",
}

def run_tool(tool_name, target):
    tool_path = ALLOWED_TOOLS.get(tool_name)
    if tool_path is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    subprocess.run([tool_path, target], check=True)
```

**Explanation:** The tool name is validated against a strict allowlist that maps to absolute paths. This prevents an attacker from specifying an arbitrary executable. The target is passed as a list argument to avoid shell interpretation. The use of absolute paths prevents PATH manipulation attacks.

### Java -- ProcessBuilder

**Before (vulnerable):**
```java
public String pingHost(String host) throws IOException {
    Process process = new ProcessBuilder("/bin/sh", "-c", "ping -c 4 " + host).start();
    return new String(process.getInputStream().readAllBytes());
}
```

**After (fixed):**
```java
public String pingHost(String host) throws IOException {
    Process process = new ProcessBuilder("ping", "-c", "4", host).start();
    return new String(process.getInputStream().readAllBytes());
}
```

**Explanation:** The shell invocation (`/bin/sh -c`) is removed. `ProcessBuilder` is called with the command and each argument as separate list elements. The `host` value is passed directly to `ping` as an argument, not through a shell.

### Java -- Runtime.exec

**Before (vulnerable):**
```java
public String listFiles(String directory) throws IOException {
    Process process = Runtime.getRuntime().exec(new String[]{
        "/bin/sh", "-c", "ls -la " + directory
    });
    return new String(process.getInputStream().readAllBytes());
}
```

**After (fixed -- native library):**
```java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.stream.Collectors;

public String listFiles(String directory) throws IOException {
    Path dir = Paths.get(directory).toRealPath();
    return Files.list(dir)
        .map(Path::toString)
        .collect(Collectors.joining("\n"));
}
```

**Explanation:** The shell command is replaced with Java's NIO `Files.list()` API, which lists directory contents natively. This eliminates command execution entirely. Note: This example should also include a path traversal check (see CWE-22) if `directory` is user-controlled.

### Node.js -- child_process.exec vs execFile

**Before (vulnerable):**
```javascript
const { exec } = require('child_process');

function pingHost(host, callback) {
  exec(`ping -c 4 ${host}`, (error, stdout, stderr) => {
    callback(error, stdout);
  });
}
```

**After (fixed):**
```javascript
const { execFile } = require('child_process');

function pingHost(host, callback) {
  execFile('ping', ['-c', '4', host], (error, stdout, stderr) => {
    callback(error, stdout);
  });
}
```

**Explanation:** `exec` is replaced with `execFile`. The key difference: `exec` spawns a shell (`/bin/sh`) to interpret the command string, while `execFile` executes the program directly without a shell. The `host` value is passed as an element in the arguments array, making shell metacharacter injection impossible.

### Node.js -- child_process.spawn

**Before (vulnerable):**
```javascript
const { spawn } = require('child_process');

function compressFile(filename) {
  const child = spawn(`gzip ${filename}`, { shell: true });
  return child;
}
```

**After (fixed):**
```javascript
const { spawn } = require('child_process');

function compressFile(filename) {
  const child = spawn('gzip', [filename]);
  return child;
}
```

**Explanation:** The `{ shell: true }` option is removed and the command string is split into the program name and an arguments array. Without `shell: true`, `spawn` executes `gzip` directly.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Manual test with injection payloads:**
   - Input: `127.0.0.1; cat /etc/passwd` -- the part after `;` should not execute.
   - Input: `127.0.0.1 | cat /etc/passwd` -- pipe should not be interpreted.
   - Input: `` 127.0.0.1 `cat /etc/passwd` `` -- backtick substitution should not execute.
   - Input: `127.0.0.1 && rm -rf /tmp/test` -- `&&` chaining should not execute.
   - Input: `$(whoami)` -- command substitution should not execute.

2. **Automated test pattern:**
   ```python
   def test_command_injection_prevented():
       # This should fail gracefully, not execute the injected command
       result = ping_host("127.0.0.1; echo INJECTED")
       assert "INJECTED" not in result
   ```

3. **Semgrep rules that should pass after fix:**
   ```yaml
   rules:
     - id: python-command-injection
       patterns:
         - pattern: subprocess.run($CMD, ..., shell=True, ...)
         - metavariable-pattern:
             metavariable: $CMD
             pattern: f"...{$VAR}..."
       message: "Command injection via subprocess with shell=True and user input"
       languages: [python]
       severity: ERROR
     - id: python-os-system
       pattern: os.system(...)
       message: "os.system is inherently unsafe; use subprocess with list args"
       languages: [python]
       severity: WARNING
   ```

### Verifying Functionality is Preserved

- Verify that the command produces the same output for valid inputs.
- Test with inputs containing spaces (arguments should be handled correctly with list execution).
- Test with special characters that are valid for the operation (e.g., filenames with spaces, domains with hyphens).
- Verify error handling: the command should report errors for invalid inputs rather than failing silently.

## Common Mistakes

1. **Using `shlex.quote` as the sole fix.** While `shlex.quote` can help, it is only effective for POSIX shells and does not protect against all injection vectors. Argument list execution is more robust and should be preferred.

2. **Removing `shell=True` but keeping a command string.** `subprocess.run("ping -c 4 host")` without `shell=True` will try to execute a program literally named `"ping -c 4 host"`, which will fail. The command must be split into a list: `["ping", "-c", "4", "host"]`.

3. **Using `shlex.split` on user-tainted strings.** `shlex.split(user_input)` still parses the string according to shell rules, which may have unexpected behavior. Build the argument list explicitly with user input only in data positions.

4. **Replacing `exec` with `execFile` but passing `{ shell: true }`.** The `execFile` function with `{ shell: true }` still spawns a shell, negating the safety benefit. Never use `{ shell: true }` with user input.

5. **Validating input with a regex but still using shell execution.** A regex like `/^[a-zA-Z0-9.]+$/` on the input is helpful defense-in-depth but does not replace proper argument list execution. Regex validation can have subtle bypasses.

6. **Hardcoding the shell path.** Do not replace one shell with another (e.g., replacing `sh -c` with `bash -c`). The goal is to eliminate shell interpretation of user input entirely.

7. **Not considering the command itself as user input.** If the user controls which command/program to execute, an allowlist of permitted commands with absolute paths is essential. Argument list execution alone does not prevent execution of arbitrary programs.

8. **Using `subprocess.run(user_input.split())`.** `str.split()` does not handle quoting, escaping, or edge cases. Build argument lists explicitly, with the program name and each argument as separate list elements.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Language not recognized** | Return error JSON. Command injection remediation requires knowing the specific process execution API. |
| **Cannot determine if shell is invoked** | Analyze the API being used. If unclear, flag for manual review. |
| **Command string is too complex to decompose** | If the command involves pipes, redirects, or complex shell features that cannot be replicated with argument list execution, flag for manual review. Provide guidance on using native libraries as alternatives. |
| **Multiple commands chained in one call** | Each command should be separated into its own `subprocess.run` (or equivalent) call with argument list execution. If the logic is complex, flag for manual review. |
| **Platform-specific commands** | Note the target platform in warnings. Windows commands (`cmd /c`, PowerShell) have different injection patterns than Unix shells. |

## Constraints

- **Preserve command functionality**: The fixed code must produce the same results for valid inputs as the original.
- **No execution**: Do not execute any commands or run the application to test the fix.
- **Prefer native libraries**: When a language-native library can replace a shell command, prefer that approach. It eliminates the entire class of command injection risk.
- **Minimal diff**: Change only the vulnerable command execution. Do not refactor surrounding code unless required for the fix.
- **No new shell execution**: The fix must not introduce new shell execution paths.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
