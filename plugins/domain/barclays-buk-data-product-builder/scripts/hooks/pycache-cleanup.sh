# Remove Python compiled files after Bash tool executes (pytest, py_compile)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-.}"

# Clean from plugin directory (templates, scripts, tests)
find "$PLUGIN_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PLUGIN_ROOT" -name "*.pyc" -delete 2>/dev/null || true

# Clean from user project directory (generated tests, session artifacts)
find generated -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find generated -name "*.pyc" -delete 2>/dev/null || true

exit 0
