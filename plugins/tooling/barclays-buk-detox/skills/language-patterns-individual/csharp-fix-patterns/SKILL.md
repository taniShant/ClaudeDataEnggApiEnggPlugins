---
name: csharp-fix-patterns
description: "C# / ASP.NET Security Fix Patterns — Provide C# and ASP.NET-specific security fix patterns and framework-specific best practices for applying CWE remediations in .NET codebases. This skill is composed with CWE-specific remediation skills"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# C# / ASP.NET Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide C# and ASP.NET-specific security fix patterns and framework-specific best practices for applying CWE remediations in .NET codebases. This skill is composed with CWE-specific remediation skills to translate generic vulnerability fixes into idiomatic C# code using ASP.NET Core middleware, Entity Framework Core, and System.Security.Cryptography APIs. It covers antiforgery token protection, authorization policies, data protection API, parameterized database queries, cryptographic operations, and input validation with data annotations and FluentValidation.

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **framework** (optional, string): The .NET framework variant (`aspnet-core`, `aspnet-mvc5`, `blazor`, `minimal-api`, `console`). Auto-detected from project files if not provided.
- **dotnet_version** (optional, string): The .NET version (e.g., `6.0`, `7.0`, `8.0`). Auto-detected from `.csproj` `TargetFramework` if not provided.

## Steps

1. **Detect framework and .NET version.**
   - Use `Glob` to find `*.csproj` or `*.sln` files.
   - Use `Read` to examine the `.csproj` for `TargetFramework` (e.g., `net8.0`, `net6.0`), package references (Microsoft.AspNetCore.*, EntityFrameworkCore), and project SDK.
   - Examine `using` directives and namespace patterns in the vulnerable file to confirm the framework.

2. **Select the appropriate fix pattern based on CWE and framework.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the .NET-version-appropriate variant (e.g., minimal APIs vs. controller-based).

3. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required `using` directives at the top of the file.
   - If the fix requires a NuGet package, note it in the output.

4. **Verify idiomatic C# conventions.**
   - Follow C# naming conventions (PascalCase for public members, camelCase for local variables, prefixed `_` for private fields).
   - Use nullable reference types (`string?` vs `string`) if enabled in the project.
   - Use `async`/`await` for asynchronous operations.
   - Use `using` declarations or `using` blocks for `IDisposable` resources.

5. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the project.
   - Apply the same fix pattern consistently.

---

## Fix Patterns

### Antiforgery Token Protection (CSRF)

#### ASP.NET Core MVC

**When to use:** CWE-352 (Cross-Site Request Forgery) in ASP.NET Core MVC applications.

**Before (vulnerable -- no antiforgery on state-changing action):**
```csharp
[HttpPost]
public IActionResult TransferFunds(TransferRequest request)
{
    _bankService.Transfer(request.FromAccount, request.ToAccount, request.Amount);
    return Ok();
}
```

**After (fixed):**
```csharp
[HttpPost]
[ValidateAntiForgeryToken]
public IActionResult TransferFunds(TransferRequest request)
{
    _bankService.Transfer(request.FromAccount, request.ToAccount, request.Amount);
    return Ok();
}
```

**Global antiforgery for all POST/PUT/DELETE (Program.cs / Startup.cs):**
```csharp
// ASP.NET Core 6+ (Program.cs)
builder.Services.AddControllersWithViews(options =>
{
    options.Filters.Add(new AutoValidateAntiforgeryTokenAttribute());
});

// Configure antiforgery options
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.Name = "__AntiForgeryCookie";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
});
```

**Razor view form with antiforgery token:**
```html
<form method="post" asp-action="TransferFunds" asp-controller="Bank">
    @Html.AntiForgeryToken()
    <input type="text" asp-for="Amount" />
    <input type="text" asp-for="ToAccount" />
    <button type="submit">Transfer</button>
</form>
```

**For API endpoints with JavaScript clients:**
```csharp
// In the controller or a dedicated endpoint
[HttpGet("antiforgery-token")]
public IActionResult GetAntiforgeryToken()
{
    var tokens = _antiforgery.GetAndStoreTokens(HttpContext);
    return Ok(new { token = tokens.RequestToken });
}
```

**Key points:**
- `AutoValidateAntiforgeryTokenAttribute` as a global filter automatically validates antiforgery tokens on all POST, PUT, PATCH, and DELETE requests.
- For APIs using JWT or API key authentication (no cookies), CSRF protection is typically not needed. Use `[IgnoreAntiforgeryToken]` explicitly with a comment explaining why.
- Razor Tag Helpers and `@Html.AntiForgeryToken()` automatically include the antiforgery hidden field.
- For SPA frontends, provide a GET endpoint to retrieve the token and include it in request headers.

#### ASP.NET Core Minimal APIs

```csharp
// .NET 7+ minimal APIs
app.MapPost("/api/transfer", [ValidateAntiForgeryToken] (TransferRequest request) =>
{
    // handler
});

// Or using endpoint filters
app.MapPost("/api/transfer", (TransferRequest request) =>
{
    // handler
}).AddEndpointFilter<AntiforgeryFilter>();
```

---

### Authorization Policies

#### Policy-Based Authorization

**When to use:** CWE-285 (Improper Authorization), CWE-862 (Missing Authorization), CWE-863 (Incorrect Authorization).

**Define policies (Program.cs):**
```csharp
builder.Services.AddAuthorization(options =>
{
    // Role-based policy
    options.AddPolicy("AdminOnly", policy =>
        policy.RequireRole("Admin"));

    // Claim-based policy
    options.AddPolicy("CanManageUsers", policy =>
        policy.RequireClaim("Permission", "UserManagement"));

    // Age-based custom policy
    options.AddPolicy("Over18", policy =>
        policy.AddRequirements(new MinimumAgeRequirement(18)));

    // Composite policy
    options.AddPolicy("SeniorAdmin", policy =>
        policy.RequireRole("Admin")
              .RequireClaim("Seniority", "Senior")
              .RequireAuthenticatedUser());

    // Fallback: deny by default
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
});
```

**Custom authorization requirement and handler:**
```csharp
using Microsoft.AspNetCore.Authorization;

public class MinimumAgeRequirement : IAuthorizationRequirement
{
    public int MinimumAge { get; }
    public MinimumAgeRequirement(int minimumAge) => MinimumAge = minimumAge;
}

public class MinimumAgeHandler : AuthorizationHandler<MinimumAgeRequirement>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        MinimumAgeRequirement requirement)
    {
        var dateOfBirthClaim = context.User.FindFirst(c => c.Type == "DateOfBirth");
        if (dateOfBirthClaim is null)
        {
            return Task.CompletedTask; // Requirement not met -- do not call Succeed
        }

        if (DateTime.TryParse(dateOfBirthClaim.Value, out var dob))
        {
            int age = DateTime.Today.Year - dob.Year;
            if (dob > DateTime.Today.AddYears(-age)) age--;
            if (age >= requirement.MinimumAge)
            {
                context.Succeed(requirement);
            }
        }

        return Task.CompletedTask;
    }
}

// Register in DI
builder.Services.AddSingleton<IAuthorizationHandler, MinimumAgeHandler>();
```

**Apply to controllers:**
```csharp
[ApiController]
[Route("api/[controller]")]
[Authorize] // Requires authentication by default
public class UsersController : ControllerBase
{
    [HttpGet]
    [Authorize(Policy = "CanManageUsers")]
    public async Task<IActionResult> GetAll()
    {
        var users = await _userService.GetAllAsync();
        return Ok(users);
    }

    [HttpDelete("{id}")]
    [Authorize(Policy = "AdminOnly")]
    public async Task<IActionResult> Delete(int id)
    {
        await _userService.DeleteAsync(id);
        return NoContent();
    }
}
```

**Resource-based authorization:**
```csharp
public class DocumentAuthorizationHandler
    : AuthorizationHandler<OperationAuthorizationRequirement, Document>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        OperationAuthorizationRequirement requirement,
        Document resource)
    {
        if (requirement.Name == "Edit" &&
            resource.AuthorId == context.User.FindFirst("sub")?.Value)
        {
            context.Succeed(requirement);
        }
        return Task.CompletedTask;
    }
}

// In the controller:
var authResult = await _authorizationService.AuthorizeAsync(
    User, document, new OperationAuthorizationRequirement { Name = "Edit" });
if (!authResult.Succeeded)
{
    return Forbid();
}
```

**Key points:**
- Use `FallbackPolicy` with `RequireAuthenticatedUser()` to enforce authentication by default on all endpoints.
- Policy-based authorization is more flexible than role-based `[Authorize(Roles = "Admin")]`.
- Custom `IAuthorizationHandler` implementations should never call `context.Fail()` unless they intend to override other handlers. Simply not calling `context.Succeed()` is sufficient to deny.
- Resource-based authorization checks ownership or specific attributes of the resource.

---

### Data Protection API

#### Protecting Sensitive Data

**When to use:** CWE-798 (Hardcoded Credentials), CWE-312 (Cleartext Storage), CWE-327 (Weak Crypto) -- for application-level encryption of sensitive data.

**Setup (Program.cs):**
```csharp
builder.Services.AddDataProtection()
    .PersistKeysToFileSystem(new DirectoryInfo("/var/keys"))
    .SetApplicationName("MySecureApp")
    .SetDefaultKeyLifetime(TimeSpan.FromDays(90))
    .ProtectKeysWithDpapi();  // Windows only -- use ProtectKeysWithCertificate for Linux
```

**Encrypt and decrypt sensitive data:**
```csharp
using Microsoft.AspNetCore.DataProtection;

public class SensitiveDataService
{
    private readonly IDataProtector _protector;

    public SensitiveDataService(IDataProtectionProvider provider)
    {
        _protector = provider.CreateProtector("SensitiveDataService.v1");
    }

    public string Protect(string plaintext)
    {
        return _protector.Protect(plaintext);
    }

    public string Unprotect(string ciphertext)
    {
        return _protector.Unprotect(ciphertext);
    }
}
```

**Time-limited data protection (for tokens, password reset links):**
```csharp
public class TokenService
{
    private readonly ITimeLimitedDataProtector _protector;

    public TokenService(IDataProtectionProvider provider)
    {
        _protector = provider
            .CreateProtector("TokenService.v1")
            .ToTimeLimitedDataProtector();
    }

    public string GenerateToken(string userId)
    {
        return _protector.Protect(userId, lifetime: TimeSpan.FromHours(24));
    }

    public string? ValidateToken(string token)
    {
        try
        {
            return _protector.Unprotect(token);
        }
        catch (CryptographicException)
        {
            return null; // Token is invalid or expired
        }
    }
}
```

**Key points:**
- The Data Protection API handles key management, rotation, and algorithm selection automatically.
- Use purpose strings (e.g., `"SensitiveDataService.v1"`) to isolate protectors. Data encrypted with one purpose cannot be decrypted with another.
- For cross-machine scenarios (web farms), persist keys to a shared location.
- `ITimeLimitedDataProtector` is ideal for expiring tokens.

---

### Entity Framework Core (Parameterized LINQ)

#### Safe Database Queries

**When to use:** CWE-89 (SQL Injection) in Entity Framework Core applications.

**Before (vulnerable -- raw SQL with interpolation):**
```csharp
public async Task<List<User>> SearchUsers(string name)
{
    var sql = $"SELECT * FROM Users WHERE Name LIKE '%{name}%'";
    return await _context.Users.FromSqlRaw(sql).ToListAsync();
}
```

**After (fixed -- FromSqlInterpolated):**
```csharp
public async Task<List<User>> SearchUsers(string name)
{
    return await _context.Users
        .FromSqlInterpolated($"SELECT * FROM Users WHERE Name LIKE {'%' + name + '%'}")
        .ToListAsync();
}
```

**After (fixed -- LINQ, fully safe):**
```csharp
public async Task<List<User>> SearchUsers(string name)
{
    return await _context.Users
        .Where(u => u.Name.Contains(name))
        .ToListAsync();
}
```

**After (fixed -- FromSqlRaw with parameters):**
```csharp
public async Task<List<User>> SearchUsers(string name)
{
    return await _context.Users
        .FromSqlRaw("SELECT * FROM Users WHERE Name LIKE {0}", $"%{name}%")
        .ToListAsync();
}
```

**Key points:**
- `FromSqlInterpolated()` is safe because it converts interpolated strings into parameterized queries. The `$"..."` syntax within `FromSqlInterpolated` creates `SqlParameter` objects, not string concatenation.
- `FromSqlRaw()` with string concatenation is vulnerable. Either use numbered placeholders (`{0}`, `{1}`) with separate parameter arguments, or switch to `FromSqlInterpolated`.
- LINQ queries (`Where`, `Select`, `OrderBy`) are always parameterized by EF Core.
- Do not confuse `FromSqlRaw($"... {variable} ...")` (vulnerable -- string interpolation happens before the method call) with `FromSqlInterpolated($"... {variable} ...")` (safe -- interpolation is captured as parameters).

#### Dynamic Column Ordering with Allowlist

```csharp
private static readonly HashSet<string> AllowedSortColumns = new(StringComparer.OrdinalIgnoreCase)
{
    "Name", "Email", "CreatedAt", "LastLogin"
};

public async Task<List<User>> GetUsersSorted(string sortColumn, bool ascending)
{
    if (!AllowedSortColumns.Contains(sortColumn))
    {
        throw new ArgumentException($"Invalid sort column: {sortColumn}");
    }

    // Use EF Core dynamic sorting with validated column
    return ascending
        ? await _context.Users.OrderBy(u => EF.Property<object>(u, sortColumn)).ToListAsync()
        : await _context.Users.OrderByDescending(u => EF.Property<object>(u, sortColumn)).ToListAsync();
}
```

---

### System.Security.Cryptography

#### Symmetric Encryption (AES-GCM)

**When to use:** CWE-327 (Weak Crypto) in .NET applications.

**Before (vulnerable -- DES with ECB):**
```csharp
using System.Security.Cryptography;

public byte[] Encrypt(byte[] data, byte[] key)
{
    using var des = DES.Create();
    des.Key = key;
    des.Mode = CipherMode.ECB;
    using var encryptor = des.CreateEncryptor();
    return encryptor.TransformFinalBlock(data, 0, data.Length);
}
```

**After (fixed -- AES-GCM, .NET 6+):**
```csharp
using System.Security.Cryptography;

public static class AesGcmEncryption
{
    private const int NonceSize = 12; // 96 bits
    private const int TagSize = 16;   // 128 bits

    public static byte[] Encrypt(byte[] plaintext, byte[] key)
    {
        byte[] nonce = RandomNumberGenerator.GetBytes(NonceSize);
        byte[] ciphertext = new byte[plaintext.Length];
        byte[] tag = new byte[TagSize];

        using var aesGcm = new AesGcm(key, TagSize);
        aesGcm.Encrypt(nonce, plaintext, ciphertext, tag);

        // Return nonce + tag + ciphertext
        byte[] result = new byte[nonce.Length + tag.Length + ciphertext.Length];
        nonce.CopyTo(result, 0);
        tag.CopyTo(result, nonce.Length);
        ciphertext.CopyTo(result, nonce.Length + tag.Length);
        return result;
    }

    public static byte[] Decrypt(byte[] encryptedData, byte[] key)
    {
        byte[] nonce = encryptedData[..NonceSize];
        byte[] tag = encryptedData[NonceSize..(NonceSize + TagSize)];
        byte[] ciphertext = encryptedData[(NonceSize + TagSize)..];
        byte[] plaintext = new byte[ciphertext.Length];

        using var aesGcm = new AesGcm(key, TagSize);
        aesGcm.Decrypt(nonce, ciphertext, tag, plaintext);
        return plaintext;
    }

    public static byte[] GenerateKey()
    {
        return RandomNumberGenerator.GetBytes(32); // 256-bit key
    }
}
```

#### Password Hashing

**Before (vulnerable -- MD5/SHA1 for passwords):**
```csharp
using System.Security.Cryptography;
using System.Text;

public string HashPassword(string password)
{
    using var md5 = MD5.Create();
    byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(password));
    return Convert.ToHexString(hash);
}
```

**After (fixed -- ASP.NET Core Identity PasswordHasher):**
```csharp
using Microsoft.AspNetCore.Identity;

public class UserService
{
    private readonly PasswordHasher<User> _hasher = new();

    public string HashPassword(User user, string password)
    {
        return _hasher.HashPassword(user, password);
    }

    public bool VerifyPassword(User user, string hashedPassword, string providedPassword)
    {
        var result = _hasher.VerifyHashedPassword(user, hashedPassword, providedPassword);
        return result == PasswordVerificationResult.Success
            || result == PasswordVerificationResult.SuccessRehashNeeded;
    }
}
```

**After (fixed -- Rfc2898DeriveBytes for PBKDF2 without ASP.NET Identity):**
```csharp
using System.Security.Cryptography;

public static class PasswordHasher
{
    private const int SaltSize = 16;
    private const int HashSize = 32;
    private const int Iterations = 600_000; // OWASP 2023 recommendation for SHA-256

    public static string Hash(string password)
    {
        byte[] salt = RandomNumberGenerator.GetBytes(SaltSize);
        byte[] hash = Rfc2898DeriveBytes.Pbkdf2(
            password,
            salt,
            Iterations,
            HashAlgorithmName.SHA256,
            HashSize);

        return $"{Convert.ToBase64String(salt)}:{Convert.ToBase64String(hash)}";
    }

    public static bool Verify(string password, string storedHash)
    {
        string[] parts = storedHash.Split(':');
        byte[] salt = Convert.FromBase64String(parts[0]);
        byte[] expectedHash = Convert.FromBase64String(parts[1]);

        byte[] actualHash = Rfc2898DeriveBytes.Pbkdf2(
            password,
            salt,
            Iterations,
            HashAlgorithmName.SHA256,
            HashSize);

        return CryptographicOperations.FixedTimeEquals(actualHash, expectedHash);
    }
}
```

**Key points:**
- `AesGcm` is available in .NET 6+. For .NET 5 and earlier, use `AesCcm` or `AesManaged` with CBC + HMAC.
- `RandomNumberGenerator.GetBytes()` is the preferred API for cryptographic random bytes (.NET 6+). For older versions, use `RandomNumberGenerator.Create().GetBytes()`.
- `CryptographicOperations.FixedTimeEquals()` provides constant-time comparison to prevent timing attacks.
- ASP.NET Core Identity's `PasswordHasher<T>` uses PBKDF2 with automatic salting and handles version upgrades.
- The .NET 6+ static `Rfc2898DeriveBytes.Pbkdf2()` method is preferred over the disposable class constructor.

---

### Input Validation

#### Data Annotations

**When to use:** CWE-20 (Improper Input Validation) in ASP.NET Core applications.

```csharp
using System.ComponentModel.DataAnnotations;

public class CreateUserRequest
{
    [Required(ErrorMessage = "Username is required")]
    [StringLength(50, MinimumLength = 3, ErrorMessage = "Username must be 3-50 characters")]
    [RegularExpression(@"^[a-zA-Z0-9_]+$", ErrorMessage = "Username must be alphanumeric")]
    public string Username { get; set; } = string.Empty;

    [Required(ErrorMessage = "Email is required")]
    [EmailAddress(ErrorMessage = "Invalid email format")]
    public string Email { get; set; } = string.Empty;

    [Required]
    [Range(13, 150, ErrorMessage = "Age must be between 13 and 150")]
    public int Age { get; set; }
}
```

**Controller with model validation:**
```csharp
[HttpPost]
public IActionResult CreateUser([FromBody] CreateUserRequest request)
{
    if (!ModelState.IsValid)
    {
        return BadRequest(ModelState);
    }
    // Process validated request
    var user = _userService.Create(request);
    return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);
}
```

**Note:** ASP.NET Core automatically validates `[ApiController]`-annotated controllers and returns 400 for invalid models without needing the `ModelState.IsValid` check.

#### FluentValidation

**When to use:** CWE-20 for complex validation rules that cannot be expressed with data annotations alone.

```csharp
using FluentValidation;

public class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Username)
            .NotEmpty().WithMessage("Username is required")
            .Length(3, 50).WithMessage("Username must be 3-50 characters")
            .Matches(@"^[a-zA-Z0-9_]+$").WithMessage("Username must be alphanumeric")
            .MustAsync(BeUniqueUsername).WithMessage("Username already taken");

        RuleFor(x => x.Email)
            .NotEmpty().WithMessage("Email is required")
            .EmailAddress().WithMessage("Invalid email format");

        RuleFor(x => x.Age)
            .InclusiveBetween(13, 150).WithMessage("Age must be between 13 and 150");
    }

    private async Task<bool> BeUniqueUsername(string username, CancellationToken ct)
    {
        // Check database for existing username
        return !await _userRepository.ExistsAsync(username, ct);
    }
}

// Register in DI (Program.cs)
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserRequestValidator>();
```

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "csharp",
  "framework": "<string: detected framework>",
  "dotnet_version": "<string: detected .NET version>",
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
  "usings_added": ["<string: new using directives>"],
  "nuget_packages_needed": [
    {
      "package_id": "<string>",
      "version": "<string>"
    }
  ],
  "configuration_changes": ["<string: Program.cs or appsettings.json changes needed>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid, compilable C# code targeting the project's .NET version.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Cannot detect framework** | Default to ASP.NET Core patterns. Set a warning recommending framework-specific review. |
| **.NET version incompatibility** | Check `TargetFramework` in `.csproj`. APIs like `AesGcm`, `RandomNumberGenerator.GetBytes()` static method, and minimal APIs require specific .NET versions. Use version-appropriate alternatives. |
| **ASP.NET MVC 5 vs ASP.NET Core** | Detect from namespace usage (`System.Web.Mvc` = MVC 5, `Microsoft.AspNetCore.Mvc` = Core). Apply the framework-appropriate pattern. |
| **Missing NuGet package** | Note the required package in `nuget_packages_needed`. Do not modify the `.csproj` directly. |
| **Nullable reference types** | Check the `<Nullable>enable</Nullable>` setting in `.csproj`. If enabled, use nullable annotations (`string?`) appropriately. |
| **Blazor Server vs Blazor WebAssembly** | Determine the hosting model from project references. Server-side Blazor has access to server resources; WebAssembly does not. |

## Constraints

- **Preserve compilation**: All generated code must compile against the project's declared `TargetFramework` and package references.
- **Respect existing patterns**: If the project uses a specific DI container, logging framework, or ORM, prefer patterns compatible with that stack.
- **No runtime execution**: Do not build or execute .NET projects to test fixes.
- **Minimal diff**: Change only the code required for the security fix.
- **Async consistency**: If the original code is synchronous and the project does not use async patterns, do not introduce async unless required by the fix. If the project is async, the fix must also be async.
- **Disposal**: Ensure `IDisposable` and `IAsyncDisposable` resources are properly disposed via `using` statements or declarations.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to build or run code.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
