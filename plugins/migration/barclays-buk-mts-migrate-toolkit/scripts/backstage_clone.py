"""Pre-flight Step 1.95 — Clone or pull the Backstage software catalogue repo."""
import os, subprocess, tempfile, glob

REPO_URL = (
    "git@app.gitlab.barcapint.com:barclays/software-catalogue/"
    "software-catalog-templates.git"
)
BRANCH = "developmentForProd"
TARGET = os.path.join(tempfile.gettempdir(), "software-catalogue-templates")

status = "FAILED"
component_count = 0

try:
    git_dir = os.path.join(TARGET, ".git")
    if os.path.isdir(git_dir):
        subprocess.run(
            ["git", "-C", TARGET, "pull", "origin", BRANCH],
            check=True, capture_output=True, text=True, timeout=120,
        )
        status = "PULLED"
    else:
        subprocess.run(
            [
                "git", "clone", "--depth", "1",
                "--branch", BRANCH, "--single-branch",
                REPO_URL, TARGET,
            ],
            check=True, capture_output=True, text=True, timeout=120,
        )
        status = "CLONED"

    components_dir = os.path.join(TARGET, "components")
    if os.path.isdir(components_dir):
        component_count = len(glob.glob(os.path.join(components_dir, "*.yaml")))
except subprocess.TimeoutExpired:
    status = "FAILED"
except subprocess.CalledProcessError as exc:
    print(f"BACKSTAGE_ERROR={exc.stderr.strip() if exc.stderr else str(exc)}")
    status = "FAILED"
except Exception as exc:
    print(f"BACKSTAGE_ERROR={exc}")
    status = "FAILED"

print(f"BACKSTAGE_REPO_PATH={TARGET}")
print(f"BACKSTAGE_REPO_STATUS={status}")
print(f"BACKSTAGE_COMPONENT_COUNT={component_count}")
