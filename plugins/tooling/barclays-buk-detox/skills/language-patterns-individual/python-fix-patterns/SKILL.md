---
name: python-fix-patterns
description: "Python Security Fix Patterns — Provide Python-specific security fix patterns and framework-specific best practices for applying CWE remediations in Python codebases. This skill is composed with CWE-specific remediation skills to tr"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Python Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide Python-specific security fix patterns and framework-specific best practices for applying CWE remediations in Python codebases. This skill is composed with CWE-specific remediation skills to translate generic vulnerability fixes into idiomatic Python code using Django, Flask, SQLAlchemy, and standard library APIs. It covers CSRF protection, ORM-safe query construction, template escaping, form validation, cryptographic operations, and secure logging practices.

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **framework** (optional, string): The Python web framework in use (`django`, `flask`, `fastapi`, `plain-python`). Auto-detected from imports and project structure if not provided.
- **python_version** (optional, string): The Python version (e.g., `3.9`, `3.11`, `3.12`). Auto-detected from `pyproject.toml`, `setup.cfg`, or runtime markers if not provided.

## Steps

1. **Detect framework and Python version.**
   - Use `Glob` to find `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements.txt`, or `Pipfile`.
   - Use `Read` to examine the dependency file for Django, Flask, FastAPI, SQLAlchemy versions.
   - Examine import statements in the vulnerable file to confirm the framework.

2. **Select the appropriate fix pattern based on CWE and framework.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the framework-specific variant (Django, Flask, plain Python).

3. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required imports at the top of the file.
   - If the fix requires a new dependency, note it in the output for the pipeline to add to `requirements.txt` or `pyproject.toml`.

4. **Verify idiomatic Python conventions.**
   - Follow PEP 8 naming conventions (snake_case functions, PascalCase classes).
   - Use type hints where the project already uses them.
   - Prefer context managers (`with` statements) for resource management.

5. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the file and project.
   - Apply the same fix pattern consistently.

---

## Fix Patterns

### CSRF Protection (Django)

#### Django CSRF Middleware and Template Tags

**When to use:** CWE-352 (Cross-Site Request Forgery) in Django applications.

**Verify middleware is enabled (settings.py):**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',       # Must be present
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Before (vulnerable -- CSRF exemption without justification):**
```python
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def transfer_funds(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        recipient = request.POST.get('recipient')
        perform_transfer(request.user, recipient, amount)
        return JsonResponse({'status': 'ok'})
```

**After (fixed):**
```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def transfer_funds(request):
    amount = request.POST.get('amount')
    recipient = request.POST.get('recipient')
    perform_transfer(request.user, recipient, amount)
    return JsonResponse({'status': 'ok'})
```

**Template form with CSRF token:**
```html
<form method="post" action="{% url 'transfer_funds' %}">
    {% csrf_token %}
    <input type="text" name="amount" />
    <input type="text" name="recipient" />
    <button type="submit">Transfer</button>
</form>
```

**For AJAX requests (Django):**
```javascript
// Include CSRF token in AJAX headers
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
fetch('/api/transfer/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ amount: 100, recipient: 'user2' }),
});
```

**Key points:**
- Never use `@csrf_exempt` on state-changing endpoints unless the endpoint uses a different authentication mechanism (e.g., API tokens) and is not accessible via browser cookies.
- Django REST Framework handles CSRF differently when using `SessionAuthentication`. Token or JWT authentication does not require CSRF.
- `CsrfViewMiddleware` must be in `MIDDLEWARE` for CSRF protection to function.

#### Flask CSRF with Flask-WTF

**When to use:** CWE-352 in Flask applications.

**Setup:**
```python
from flask import Flask
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']  # From environment
csrf = CSRFProtect(app)
```

**Form with CSRF protection:**
```python
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField
from wtforms.validators import DataRequired, NumberRange

class TransferForm(FlaskForm):
    recipient = StringField('Recipient', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
```

**Template:**
```html
<form method="post">
    {{ form.hidden_tag() }}
    {{ form.recipient.label }} {{ form.recipient() }}
    {{ form.amount.label }} {{ form.amount() }}
    <button type="submit">Transfer</button>
</form>
```

---

### SQL Injection Prevention (Django ORM and SQLAlchemy)

#### Django ORM Safe Queries

**When to use:** CWE-89 in Django applications.

**Before (vulnerable -- raw SQL with string formatting):**
```python
def search_users(request):
    name = request.GET.get('name')
    users = User.objects.raw(f"SELECT * FROM auth_user WHERE username LIKE '%{name}%'")
    return render(request, 'users.html', {'users': users})
```

**After (fixed -- ORM queryset):**
```python
def search_users(request):
    name = request.GET.get('name', '')
    users = User.objects.filter(username__icontains=name)
    return render(request, 'users.html', {'users': users})
```

**After (fixed -- raw SQL with params when ORM is insufficient):**
```python
def search_users(request):
    name = request.GET.get('name', '')
    users = User.objects.raw(
        "SELECT * FROM auth_user WHERE username LIKE %s",
        ['%' + name + '%']
    )
    return render(request, 'users.html', {'users': users})
```

**After (fixed -- extra() replacement with annotate):**
```python
from django.db.models import Value, CharField
from django.db.models.functions import Concat

# Avoid: User.objects.extra(where=["username = '%s'" % name])
# Use ORM instead:
users = User.objects.filter(username=name)
```

**Key points:**
- Django ORM methods (`filter()`, `exclude()`, `get()`) automatically parameterize queries.
- `objects.raw()` is safe only when parameters are passed as the second argument (list or dict), never interpolated into the SQL string.
- `objects.extra()` is deprecated and prone to injection. Replace with ORM expressions (`annotate`, `F()`, `Q()`).
- `connection.cursor().execute()` must use parameterized queries: `cursor.execute("SELECT ... WHERE id = %s", [user_id])`.

#### SQLAlchemy Parameterized Queries

**When to use:** CWE-89 when SQLAlchemy is used outside of Django.

**Before (vulnerable):**
```python
from sqlalchemy import create_engine

def get_user(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            "SELECT * FROM users WHERE username = '" + username + "'"
        )
        return result.fetchone()
```

**After (fixed -- text() with bound parameters):**
```python
from sqlalchemy import create_engine, text

def get_user(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username}
        )
        return result.fetchone()
```

**After (fixed -- ORM session query):**
```python
from sqlalchemy.orm import Session

def get_user(session: Session, username: str):
    return session.query(User).filter(User.username == username).first()
```

**After (fixed -- SQLAlchemy 2.0 select() style):**
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

def get_user(session: Session, username: str):
    stmt = select(User).where(User.username == username)
    return session.scalars(stmt).first()
```

**Key points:**
- Always wrap raw SQL strings in `text()` and pass parameters as a dict.
- Prefer the ORM query API or `select()` construct over raw SQL.
- SQLAlchemy 2.0 deprecates `session.query()` in favor of `select()`. Use the style matching the project's SQLAlchemy version.

---

### Template Escaping (Django and Jinja2)

#### Django Template Auto-Escaping

**When to use:** CWE-79 (XSS) in Django templates.

**Before (vulnerable -- disabling autoescape):**
```html
{% autoescape off %}
<div class="bio">{{ user.bio }}</div>
{% endautoescape %}
```

**After (fixed):**
```html
<div class="bio">{{ user.bio }}</div>
```

**Before (vulnerable -- |safe filter on untrusted input):**
```html
<div class="comment">{{ comment.body|safe }}</div>
```

**After (fixed -- remove |safe, or sanitize server-side):**
```html
<!-- Option 1: Let autoescape handle it -->
<div class="comment">{{ comment.body }}</div>

<!-- Option 2: If HTML rendering is needed, sanitize server-side with bleach -->
<div class="comment">{{ comment.sanitized_body|safe }}</div>
```

**Server-side sanitization with bleach:**
```python
import bleach

ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
ALLOWED_PROTOCOLS = ['http', 'https']

def sanitize_html(raw_html):
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
```

**Key points:**
- Django auto-escapes template variables by default. Do not disable this.
- The `|safe` filter marks content as safe and bypasses escaping. Only use it on content that has been explicitly sanitized server-side.
- `{% autoescape off %}` disables escaping for an entire block. Remove it unless every variable in the block is known-safe.
- Use `mark_safe()` in Python view code only for content you fully control (e.g., generated HTML from trusted logic), never for user input.

#### Flask / Jinja2 Auto-Escaping

**When to use:** CWE-79 in Flask applications.

**Ensure auto-escaping is enabled (it is by default for .html, .htm, .xml, .xhtml):**
```python
app = Flask(__name__)
# Jinja2 auto-escaping is ON by default for HTML templates
```

**Before (vulnerable -- Markup() on user input):**
```python
from markupsafe import Markup

@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    return render_template('greet.html', name=Markup(name))  # Bypasses escaping
```

**After (fixed):**
```python
@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    return render_template('greet.html', name=name)  # Auto-escaped in template
```

**Before (vulnerable -- |safe filter in Jinja2 template):**
```html
<p>{{ user_comment|safe }}</p>
```

**After (fixed):**
```html
<p>{{ user_comment }}</p>
```

**Key points:**
- Jinja2 auto-escaping is enabled by default in Flask for HTML templates.
- Never wrap user input in `Markup()` or `markupsafe.Markup()` -- this marks it as safe and bypasses escaping.
- The `|safe` filter in Jinja2 templates has the same effect as `|safe` in Django. Remove it for untrusted data.
- For non-HTML templates (e.g., `.txt`, `.csv`), auto-escaping may be off. Use the `|e` filter explicitly or configure auto-escaping for those extensions.

---

### Flask Security Best Practices (Blueprints and Middleware)

#### Flask Blueprint Structure for Security Boundaries

**When to use:** CWE-285 (Improper Authorization), general security architecture.

```python
from flask import Blueprint, abort
from functools import wraps
from flask_login import current_user, login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_role(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_role(role):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin_bp.route('/users')
@require_role('admin')
def list_users():
    return render_template('admin/users.html', users=User.query.all())
```

#### Flask Security Headers

```python
from flask import Flask
from flask_talisman import Talisman

app = Flask(__name__)

# flask-talisman sets security headers including CSP, HSTS, X-Frame-Options
talisman = Talisman(
    app,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self' 'unsafe-inline'",
    },
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    session_cookie_http_only=True,
)
```

---

### Cryptographic Operations

#### Using the cryptography Library

**When to use:** CWE-327 (Weak Crypto) in Python applications.

**Symmetric encryption with Fernet (AES-128-CBC + HMAC-SHA256):**
```python
from cryptography.fernet import Fernet

# Key generation (store securely, not in code)
key = Fernet.generate_key()

def encrypt(data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data)

def decrypt(token: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.decrypt(token)
```

**AES-GCM for custom encryption:**
```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
    """Encrypt data with AES-256-GCM. Returns nonce + ciphertext."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)
    return nonce + ciphertext

def decrypt_aes_gcm(encrypted: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM data. Expects nonce + ciphertext."""
    aesgcm = AESGCM(key)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)

def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)
```

**Password hashing with argon2:**
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
```

**Before (vulnerable -- hashlib.md5 for security):**
```python
import hashlib

def generate_token(user_id):
    return hashlib.md5(str(user_id).encode()).hexdigest()
```

**After (fixed -- HMAC with SHA-256):**
```python
import hmac
import hashlib
import os

SECRET_KEY = os.environ['TOKEN_SECRET_KEY']

def generate_token(user_id):
    return hmac.new(
        SECRET_KEY.encode(),
        str(user_id).encode(),
        hashlib.sha256
    ).hexdigest()
```

**Key points:**
- Prefer `cryptography` library over `pycryptodome` for new projects.
- `Fernet` is the simplest safe option for symmetric encryption; it handles IV, padding, and HMAC internally.
- Use `os.urandom()` or `secrets` module for cryptographic random bytes, never `random`.
- For password hashing, use `argon2-cffi` (preferred) or `bcrypt`. Never use `hashlib` directly.

---

### Logging Best Practices

#### Secure Logging Configuration

**When to use:** CWE-200 (Information Exposure), CWE-532 (Information Exposure Through Log Files).

**Before (vulnerable -- logging sensitive data):**
```python
import logging

logger = logging.getLogger(__name__)

def authenticate(username, password):
    logger.info(f"Login attempt: username={username}, password={password}")
    user = User.objects.get(username=username)
    if not user.check_password(password):
        logger.error(f"Failed login for {username} with password {password}")
        raise AuthenticationError("Invalid credentials")
    logger.info(f"Successful login for {username}, session_token={user.session_token}")
    return user
```

**After (fixed):**
```python
import logging

logger = logging.getLogger(__name__)

def authenticate(username, password):
    logger.info("Login attempt for user: %s", username)
    user = User.objects.get(username=username)
    if not user.check_password(password):
        logger.warning("Failed login attempt for user: %s", username)
        raise AuthenticationError("Invalid credentials")
    logger.info("Successful login for user: %s", username)
    return user
```

**Structured logging configuration:**
```python
import logging
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'filters': {
        'sensitive_data_filter': {
            '()': 'myapp.logging_filters.SensitiveDataFilter',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/myapp/app.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'standard',
            'filters': ['sensitive_data_filter'],
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file'],
    },
}
```

**Sensitive data filter:**
```python
import logging
import re

class SensitiveDataFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r'password\s*[=:]\s*\S+', re.IGNORECASE), 'password=***REDACTED***'),
        (re.compile(r'token\s*[=:]\s*\S+', re.IGNORECASE), 'token=***REDACTED***'),
        (re.compile(r'secret\s*[=:]\s*\S+', re.IGNORECASE), 'secret=***REDACTED***'),
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '***SSN***'),
    ]

    def filter(self, record):
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()
        return True
```

**Key points:**
- Never log passwords, tokens, session IDs, credit card numbers, or PII.
- Use `logger.info("message: %s", variable)` (lazy formatting) instead of f-strings for logging. This avoids string formatting if the log level is not active and is safer with sensitive data filters.
- Apply log rotation to prevent disk exhaustion.
- Use structured logging (e.g., `python-json-logger`) for production systems to enable easier log analysis.
- Set log file permissions to restrict access (e.g., `chmod 640`).

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "python",
  "framework": "<string: detected framework>",
  "python_version": "<string: detected Python version>",
  "pattern_applied": "<string: name of the pattern applied>",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer>",
      "original_code": "<string>",
      "fixed_code": "<string>",
      "pattern": "<string: pattern name used>"
    }
  ],
  "imports_added": ["<string: new import statements>"],
  "dependencies_needed": ["<string: package names to add to requirements>"],
  "configuration_changes": ["<string: settings.py or config changes needed>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid, syntactically correct Python code.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Cannot detect framework** | Default to plain Python patterns. Set a warning recommending framework-specific review. |
| **Django version incompatibility** | Check Django version for API differences (e.g., `path()` vs `url()`, middleware style). Apply the version-appropriate pattern. |
| **SQLAlchemy 1.x vs 2.x** | Detect version from dependencies. Use `session.query()` for 1.x and `select()` for 2.x. |
| **Missing dependency** | Note the required package in `dependencies_needed`. Do not modify `requirements.txt` directly. |
| **Python 2 code detected** | Flag for manual review. Python 2 is end-of-life. Note the pattern but warn about the unsupported version. |
| **Async code (FastAPI, async Flask)** | Ensure fix patterns use `async`/`await` where the existing code is async. Do not mix sync and async database calls. |

## Constraints

- **Preserve functionality**: All generated code must be syntactically valid Python and semantically equivalent to the original for valid inputs.
- **Respect existing style**: Match the project's existing code style (type hints, docstrings, import ordering).
- **No runtime execution**: Do not execute Python code to test fixes.
- **Minimal diff**: Change only the code required for the security fix.
- **Framework consistency**: If the project uses Django ORM, do not introduce SQLAlchemy patterns and vice versa.
- **Dependency awareness**: Note new dependencies but do not install them. The pipeline handles dependency management.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
