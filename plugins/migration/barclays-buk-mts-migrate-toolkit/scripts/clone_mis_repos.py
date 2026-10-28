"""
clone_mis_repos.py — Clone MIS EGS/EBS source repos from GitLab to ~/.mts-source/

Usage:
    python3 clone_mis_repos.py <jar_name>

Examples:
    python3 clone_mis_repos.py egs_odsmfcustomer-07.0045.001
    python3 clone_mis_repos.py cust-update-15.10.001
    python3 clone_mis_repos.py ebs_memenquiry-03.0011

Output (printed to stdout, one per line):
    MIS_REPO_STATUS=ALREADY_EXISTS|CLONED|NOT_MAPPED|CLONE_FAILED
    MIS_REPO_PATH=/path/to/cloned/repo  (only if ALREADY_EXISTS or CLONED)
    MIS_REPO_NAME=<repo-name>            (only if found in mapping)

Notes:
    - Auth handled by PAT token URL rewrite in ~/.gitconfig
    - Cache dir: ~/.mts-source/ (persistent across sessions)
    - Already-cloned repos are reused without re-cloning
"""

import os
import re
import subprocess
import sys
import urllib.parse

GITLAB_BASE = "https://app.gitlab.barcapint.com/barclays/mca/legacy/mis"
CACHE_DIR = os.path.expanduser("~/.mts-source")

# Mapping: JAR name prefix (regex) -> MIS repo path relative to GITLAB_BASE
# Format: (pattern, "subgroup/repo-name")
#
# Key insight: most EBS service JARs (cust-update, screeningenquiry, bus-unit-emp,
# ebs_custenquiry) all route their mainframe calls through egs-odsmf-customer gateway.
# Their Transaction/DataGroup classes live in egs-odsmf-customer, not separate repos.
JAR_TO_REPO = [
    # EGS gateways (WMOD fields + Transaction classes)
    (r"egs_odsmfcustomer",       "gateways/egs-odsmf-customer"),
    (r"egs_odsmfmember",         "gateways/egs-odsmf-member"),
    (r"egs_odsmfukba",           "gateways/egs-odsmf-ukba"),
    (r"egs_product",             "gateways/egs-odsmf-customer"),   # ProductGateway uses same EGS

    # EBS services whose Transaction classes live in egs-odsmf-customer
    # (confirmed by checking local /tmp/mts-source/egs-odsmf-customer file list)
    (r"cust-update",             "gateways/egs-odsmf-customer"),   # CustomerUpdateTransaction.java
    (r"screeningenquiry",        "gateways/egs-odsmf-customer"),   # CustomerScreeningTransaction.java
    (r"bus-unit-emp",            "gateways/egs-odsmf-customer"),   # BusinessUnitEmployeeDataGroup.java
    (r"ebs_custenquiry",         "gateways/egs-odsmf-customer"),   # LimitsDataGroup.java, LimitsRetrieveTransaction.java

    # EBS services with their own repos
    (r"ebs_custpersonal",        "services/customer-personal"),
    (r"ebs_custlocate",          "services/customer-locate"),
    (r"ebs_memenquiry",          "services/membership-enquiry"),
    (r"ebs_memprocenquiry",      "services/membership-process-enquiry"),
    (r"ebs_memmaintenance",      "services/membership-maintenance"),
    (r"ebs_custholdings",        "services/customerprocess-enquiry"),
    (r"ebs_cchlifecycle",        "services/customercontacthistory-lifecycle"),
    (r"ebs_cchquery",            "services/customercontacthistory-lifecycle"),

    # EGS gateways — non-ODS-MF (different backend systems)
    # These repo paths are UNVERIFIED — derived from naming convention.
    # If clone fails, S.4 JAR search will still extract from local Gradle cache JARs.
    (r"egs_mortgages",           "gateways/egs-mortgages"),         # MortgagesGateway (ILP/Hogan SOAP)
    (r"ebs_mortacctenquiry",     "services/mortgage-account-enquiry"),  # MortgageAccountEnquiry EBS
    (r"egs_loans",               "gateways/egs-loans"),             # LoansGateway (ALS backend)
    (r"ebs_loansenquiry",        "services/loans-enquiry"),         # LoansEnquiryService EBS
    (r"egs_bonds",               "gateways/egs-bonds"),             # BondsGateway (oracle-db-direct)
    (r"ebs_bondproduct",         "services/bond-product"),          # ProductBondService EBS
    (r"ebs_auditlifecycle",      "services/audit-lifecycle"),       # AuditLifecycle EBS
    (r"egs_audit",               "gateways/egs-audit"),             # AuditGateway (write to mainframe)
    (r"ebs_execctxemployee",     "services/execution-context-employee"),  # EmployeeService EBS (ITSU/Oracle)
]


def find_repo(jar_name: str):
    """Return (repo_path, matched_pattern) or (None, None) if not mapped."""
    name = jar_name.lower()
    # Primary match: try jar name as-is against each pattern
    for pattern, repo_path in JAR_TO_REPO:
        if re.search(pattern, name, re.IGNORECASE):
            return repo_path, pattern
    # Fallback: strip underscores from the jar name only, then retry against
    # each pattern with underscores made optional. This handles variant jar
    # names like "egs_odsmf_customer" (extra underscore) matching canonical
    # pattern "egs_odsmfcustomer" without altering the pattern's semantics.
    # We insert "_?" after each underscore position in the pattern, making
    # underscores optional in the normalized name rather than removing them
    # from the pattern entirely (which could cause false positive matches).
    normalized_name = name.replace("_", "")
    for pattern, repo_path in JAR_TO_REPO:
        # Make underscores optional: "egs_odsmfcustomer" → "egs_?odsmfcustomer"
        flexible_pattern = pattern.replace("_", "_?")
        if re.search(flexible_pattern, normalized_name, re.IGNORECASE):
            return repo_path, pattern
    return None, None


def clone_repo(repo_path: str) -> tuple:
    """
    Clone repo_path to CACHE_DIR/<repo-name>.
    Returns (status, local_path) where status is ALREADY_EXISTS, CLONED, or CLONE_FAILED.
    """
    repo_name = repo_path.split("/")[-1]
    local_path = os.path.join(CACHE_DIR, repo_name)

    git_head = os.path.join(local_path, ".git", "HEAD")
    if os.path.isdir(local_path) and os.path.isfile(git_head):
        return "ALREADY_EXISTS", local_path

    if os.path.isdir(local_path):
        # Partial/broken clone from a previous failed attempt — skip, report as failed
        return "CLONE_FAILED", None

    os.makedirs(CACHE_DIR, exist_ok=True)

    encoded_path = urllib.parse.quote(repo_path, safe='/')
    clone_url = f"{GITLAB_BASE}/{encoded_path}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", clone_url, local_path],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return "CLONED", local_path
    else:
        return "CLONE_FAILED", None


def main():
    if len(sys.argv) < 2:
        print("Usage: clone_mis_repos.py <jar_name>")
        print("MIS_REPO_STATUS=NOT_MAPPED")
        sys.exit(0)

    jar_name = sys.argv[1]
    repo_path, _ = find_repo(jar_name)

    if repo_path is None:
        print(f"MIS_REPO_STATUS=NOT_MAPPED")
        print(f"# JAR '{jar_name}' has no MIS repo mapping. Add to JAR_TO_REPO if known.")
        sys.exit(0)

    repo_name = repo_path.split("/")[-1]
    status, local_path = clone_repo(repo_path)

    print(f"MIS_REPO_STATUS={status}")
    print(f"MIS_REPO_NAME={repo_name}")
    if local_path:
        print(f"MIS_REPO_PATH={local_path}")

    if status == "CLONE_FAILED":
        print(f"# Failed to clone {GITLAB_BASE}/{repo_path}.git")
        print(f"# Check network access and ~/.gitconfig PAT token URL rewrite")
        sys.exit(1)


if __name__ == "__main__":
    main()
